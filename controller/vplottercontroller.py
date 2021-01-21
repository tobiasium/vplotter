#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
V-Plotter controller in PyQt for GRBL v-plotter

author: Tobias Witting witting@mbi-berlin.de
version history:
2020-12-22: TW created this
"""

import sys
import os
import re
import time
import datetime
import numpy as np
from pyqtgraph import QtGui, QtCore
import pyqtgraph as pg
from pyqtgraph.ptime import time as pyqtgtime
from qtguielements import StartStopButtons, PlottingTimer, Spinner
from generaltools import gettimestamp, sec2HMS
import serial
from serial.tools.list_ports import comports

pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')


class vplottercontroller(QtGui.QWidget):
    """GUI for GRBL in PyQt."""

    def __init__(self):
        """Initialise."""
        super(vplottercontroller, self).__init__()
        self.initUI()

    def initUI(self):
        """Initialise the GUI."""
        self.usemock = False
        hbmain = QtGui.QHBoxLayout()
        
        self.plt1 = pg.PlotWidget()
        self.plt1.setLabel('left', "y (mm)")
        self.plt1.setLabel('bottom', "x (mm)")
        self.plt1.showGrid(x=True, y=True)
        self.plt_headposition_x = pg.InfiniteLine(angle=90, movable=False)
        self.plt_headposition_y = pg.InfiniteLine(angle=0, movable=False)
        self.plt1.addItem(self.plt_headposition_x)
        self.plt1.addItem(self.plt_headposition_y)
        self.plt_gcode = self.plt1.plot(pen=pg.mkPen('r', width=2))
        self.plt1.setAspectLocked(True,ratio=1)
        
        hbmain.addWidget(self.plt1)
        
        
        vbconsole = QtGui.QVBoxLayout()
        gb = QtGui.QGroupBox('console:')
        gbvb = QtGui.QVBoxLayout()
        
        gbvbhb = QtGui.QHBoxLayout()
        self.gui_console_date_cb = QtGui.QCheckBox('show date', self, checkable=True, checked=False)
        self.gui_console_time_cb = QtGui.QCheckBox('show time', self, checkable=True, checked=False)
        gbvbhb.addWidget(self.gui_console_date_cb)
        gbvbhb.addWidget(self.gui_console_time_cb)
        gbvb.addLayout(gbvbhb)

        self.gui_consoletext = QtGui.QTextEdit()
        gbvb.addWidget(self.gui_consoletext)
        
        self.gui_command = QtGui.QLineEdit('', self)
        self.gui_command.returnPressed.connect(self.respond_gui_command)
        gbvb.addWidget(self.gui_command)
        
        gb.setLayout(gbvb)
        vbconsole.addWidget(gb)

        hbmain.addLayout(vbconsole)


        vbcontrols = QtGui.QVBoxLayout()
        
        gb = QtGui.QGroupBox('connection:')
        gbvb = QtGui.QVBoxLayout()
        hbox = QtGui.QHBoxLayout()
        pb = QtGui.QPushButton("Scan")
        pb.clicked.connect(self.scan)
        self.scanbtn = pb
        hbox.addWidget(pb)
        cb=QtGui.QComboBox()
        self.port_list=cb
        self.port_list.setMinimumWidth(200)
        hbox.addWidget(cb)
        cb=QtGui.QCheckBox("Open")
        self.opened=cb
        cb.stateChanged.connect(self.toggle_connection)
        hbox.addWidget(cb)
        gbvb.addLayout(hbox)
        gb.setLayout(gbvb)
        vbcontrols.addWidget(gb)

        # gb = QtGui.QGroupBox('controls:')
        # gbvb = QtGui.QVBoxLayout()
        # gbvbhb = QtGui.QHBoxLayout()
        # btn = QtGui.QPushButton('unlock')
        # btn.clicked.connect(self.unlock)
        # gbvbhb.addWidget(btn)
        # btn = QtGui.QPushButton('FEED HOLD')
        # btn.clicked.connect(self.feed_hold)
        # gbvbhb.addWidget(btn)
        # btn = QtGui.QPushButton('RESUME')
        # btn.clicked.connect(self.feed_resume)
        # gbvbhb.addWidget(btn)
        # gbvb.addLayout(gbvbhb)
        # gb.setLayout(gbvb)
        # vbcontrols.addWidget(gb)

        gb = QtGui.QGroupBox('main:')
        gbvb = QtGui.QVBoxLayout()
        
        
        gbvbhb = QtGui.QHBoxLayout()
        btn = QtGui.QPushButton('unlock')
        btn.clicked.connect(self.unlock)
        gbvbhb.addWidget(btn)
        
        self.motorlock_enable_cb = QtGui.QCheckBox('motorlock', self, checkable=True, checked=True)
        self.motorlock_enable_cb.clicked.connect(self.motorlock_toggle)
        gbvbhb.addWidget(self.motorlock_enable_cb)
        
        btn = QtGui.QPushButton('set MCS zero (home)!')
        btn.clicked.connect(self.gui_set_mcs_zero)
        gbvbhb.addWidget(btn)
        btn = QtGui.QPushButton('set WCS zero!')
        btn.clicked.connect(self.gui_set_wcs_zero)
        gbvbhb.addWidget(btn)
        gbvb.addLayout(gbvbhb)
        
        gbvbhb = QtGui.QHBoxLayout()
        btn = QtGui.QPushButton('G0 go to MCS origin')
        btn.clicked.connect(self.go_to_mcs_origin)
        gbvbhb.addWidget(btn)
        btn = QtGui.QPushButton('G0 go to WCS origin')
        btn.clicked.connect(self.go_to_wcs_origin)
        gbvbhb.addWidget(btn)
        gbvb.addLayout(gbvbhb)

        gb.setLayout(gbvb)
        vbcontrols.addWidget(gb)

        gb = QtGui.QGroupBox('position:')
        gbvb = QtGui.QVBoxLayout()
        gbvbhb = QtGui.QHBoxLayout()
        btn = QtGui.QPushButton('get state')
        btn.clicked.connect(self.gui_get_state)
        gbvbhb.addWidget(btn)
        self.gui_get_state_online_cb = QtGui.QCheckBox('online', self, checkable=True, checked=False)
        self.gui_get_state_online_cb.clicked.connect(self.gui_get_state_online_cb_clicked)
        gbvbhb.addWidget(self.gui_get_state_online_cb)
        
        
        
        gbvb.addLayout(gbvbhb)
        
        gbvbhb = QtGui.QHBoxLayout()
        self.gui_info_state1 = QtGui.QLabel('state', self)
        self.gui_info_state2 = QtGui.QLabel('state', self)
        self.gui_info_mcs_x = QtGui.QLabel('MCS x', self)
        self.gui_info_mcs_y = QtGui.QLabel('MCS y', self)
        self.gui_info_wcs_x = QtGui.QLabel('WCS x', self)
        self.gui_info_wcs_y = QtGui.QLabel('WCS y', self)        
        
        gbvb.addWidget(self.gui_info_state1)
        gbvb.addWidget(self.gui_info_state2)
        
        gbvbhb = QtGui.QHBoxLayout()
        gbvbhb.addWidget(self.gui_info_mcs_x)
        gbvbhb.addWidget(self.gui_info_mcs_y)
        # gbvb.addLayout(gbvbhb)
        
        #gbvbhb = QtGui.QHBoxLayout()
        gbvbhb.addWidget(self.gui_info_wcs_x)
        gbvbhb.addWidget(self.gui_info_wcs_y)
        gbvb.addLayout(gbvbhb)

        gbvb.addLayout(gbvbhb)
        
        gb.setLayout(gbvb)
        vbcontrols.addWidget(gb)
        
        

        

        gb = QtGui.QGroupBox('jogging controls:')
        gbvb = QtGui.QVBoxLayout()
        
        gbvbhb = QtGui.QHBoxLayout()
        #btn = QtGui.QPushButton('1')
        #btn.clicked.connect(self.unlock)
        #gbvbhb.addWidget(btn)
        self.gui_jog_stepsize = Spinner('jog step size (mm):', 1, step=1, guic=gbvbhb)
        self.gui_jog_feedrate = Spinner('feed rate (mm/min):', 5000, step=100, guic=gbvbhb)
        gbvb.addLayout(gbvbhb)

        horizontalGroupBox = QtGui.QGroupBox("")
        layout = QtGui.QGridLayout()
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 1)
        
        def set_jogfun(what):
            def fun():
                self.jog(what)
            return fun
        
        
        #d = {'what': '-x +y', 'n': 0, 'm': 0}
        
        def makebutton(d):
            btn = QtGui.QPushButton(d['what'])
            btn.clicked.connect(set_jogfun(d['what']))
            layout.addWidget(btn,d['n'],d['m'])
            
        makebutton({'what': '-x +y', 'n': 0, 'm': 0})   
        makebutton({'what': '+y',    'n': 0, 'm': 1})   
        makebutton({'what': '+x +y', 'n': 0, 'm': 2})   

        makebutton({'what': '-x',    'n': 1, 'm': 0})   
        # makebutton({'what': '',      'n': 1, 'm': 1})   
        makebutton({'what': '+x',    'n': 1, 'm': 2})   

        makebutton({'what': '-x -y', 'n': 2, 'm': 0})   
        makebutton({'what': '-y',    'n': 2, 'm': 1})   
        makebutton({'what': '+x -y', 'n': 2, 'm': 2})        
        
        horizontalGroupBox.setLayout(layout)
        gbvb.addWidget(horizontalGroupBox)
        
        gb.setLayout(gbvb)
        vbcontrols.addWidget(gb)
        
        
        gb = QtGui.QGroupBox('absolute positioning:')
        gbvb = QtGui.QVBoxLayout()
        
        
        
        gbvbhb = QtGui.QHBoxLayout()
        self.gui_g1_xpos_mm = Spinner('x (mm):', 0, step=1, guic=gbvbhb)
        self.gui_g1_ypos_mm = Spinner('y (mm):', 0, step=1, guic=gbvbhb)
        gbvb.addLayout(gbvbhb)
        self.gui_g1_feedrate = Spinner('feed rate (mm/min):', 5000, step=100, guic=gbvb)
        
        gbvbhb = QtGui.QHBoxLayout()
        btn = QtGui.QPushButton('G0 GO')
        btn.clicked.connect(self.g0_go_to_position)
        gbvbhb.addWidget(btn)
        btn = QtGui.QPushButton('G1 GO')
        btn.clicked.connect(self.g1_go_to_position)
        gbvbhb.addWidget(btn)
        gbvb.addLayout(gbvbhb)
        
        gb.setLayout(gbvb)
        vbcontrols.addWidget(gb)
        
        
        gb = QtGui.QGroupBox('spindle control:')
        gbvb = QtGui.QVBoxLayout()
        
        gbvbhb = QtGui.QHBoxLayout()
        self.gui_spindlespeed = Spinner('spindle / servo:', 600, step=50, bounds=[0, 1000], guic=gbvbhb, fun=self.set_spindle_speed)
        
        self.gui_spindle_enable_cb = QtGui.QCheckBox('Spindle', self, checkable=True, checked=False)
        self.gui_spindle_enable_cb.clicked.connect(self.gui_spindle_enable_cb_clicked)
        gbvbhb.addWidget(self.gui_spindle_enable_cb)
        
        #btn = QtGui.QPushButton('ON')
        #btn.clicked.connect(self.set_spindle_on)
        #gbvbhb.addWidget(btn)
        #btn = QtGui.QPushButton('OFF')
        #btn.clicked.connect(self.set_spindle_off)
        #gbvbhb.addWidget(btn)
        
        gbvb.addLayout(gbvbhb)
        gb.setLayout(gbvb)
        vbcontrols.addWidget(gb)
        
        
        
        gb = QtGui.QGroupBox('G-code streaming:')
        gbvb = QtGui.QVBoxLayout()
        
        gbvbhb = QtGui.QHBoxLayout()
        l = QtGui.QLabel('file:')
        gbvbhb.addWidget(l)
        self.gcodefile_text = QtGui.QTextEdit(os.path.join(os.path.expanduser('~'), 'test.gcode'))
        self.gcodefile_text.setMinimumWidth(150)
        self.gcodefile_text.setMaximumHeight(30)
        gbvbhb.addWidget(self.gcodefile_text)
        btn = QtGui.QPushButton('...')
        btn.clicked.connect(self._browse_gcodefile)
        gbvbhb.addWidget(btn)
        btn = QtGui.QPushButton('load')
        btn.clicked.connect(self.gcode_load_file)
        gbvbhb.addWidget(btn)
        gbvb.addLayout(gbvbhb)
        
        gbvbhb = QtGui.QHBoxLayout()
        self.gcode_stream_progressbar = QtGui.QProgressBar(self)
        gbvbhb.addWidget(self.gcode_stream_progressbar)
        
        
        btn = QtGui.QPushButton('start streaming')
        btn.clicked.connect(self.gcode_stream_start)
        gbvbhb.addWidget(btn)
        btn = QtGui.QPushButton('stop streaming')
        btn.clicked.connect(self.gcode_stream_stop)
        gbvbhb.addWidget(btn)
        gbvb.addLayout(gbvbhb)
        
        self.gui_eta_info = QtGui.QLabel('--- streaming ETA info ---', self)
        gbvb.addWidget(self.gui_eta_info)
        
        gbvb.addLayout(gbvbhb)
        gb.setLayout(gbvb)
        vbcontrols.addWidget(gb)
        
        gb = QtGui.QGroupBox('')
        gbhb = QtGui.QHBoxLayout()
        
        btn = QtGui.QPushButton('FEED HOLD')
        btn.clicked.connect(self.feed_hold)
        btn.setMinimumHeight(60)
        gbhb.addWidget(btn)
        btn = QtGui.QPushButton('RESUME')
        btn.clicked.connect(self.feed_resume)
        btn.setMinimumHeight(60)
        gbhb.addWidget(btn)
        
        gb.setLayout(gbhb)
        vbcontrols.addWidget(gb)
        
        
        
        hbmain.addLayout(vbcontrols)
        hbmain.setStretch(0,2)
        hbmain.setStretch(1,1)
        hbmain.setStretch(2,1)
        
        self.setLayout(hbmain)
        self.setGeometry(20, 40, 1400, 900)
        self.setWindowTitle('Vplotter Controller')
        self.setStyleSheet("font-size: 12pt")
        self.show()
        self.scan()
        
        self.get_state_timer = QtCore.QTimer()
        self.get_state_timer.timeout.connect(self.gui_get_state)
        self.serial_active = False
        self.gcode_stream_running = False


    def userinfo(self, txt):
        """Set userinfo to gui."""
        timestamptxt = None
        if self.gui_console_date_cb.isChecked() and self.gui_console_time_cb.isChecked():
            timestamptxt = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if not self.gui_console_date_cb.isChecked() and self.gui_console_time_cb.isChecked():
            timestamptxt = datetime.datetime.now().strftime('%H:%M:%S')
        
        if timestamptxt is not None:
            self.gui_consoletext.append("%s: %s" % (timestamptxt, txt))
        else:
            self.gui_consoletext.append("%s" % txt)
        self.gui_consoletext.moveCursor(QtGui.QTextCursor.End)
        # print("%s: %s" % (timestamptxt, txt))


    def scan(self):
        """Scan for serial ports with controllers attached."""
        self.port_list.clear()
        self.port_list.addItem('scanning for COMports, pls wait...')
        QtGui.QApplication.processEvents()
        
        self.port_list.clear()
        for port, desc, hwid in sorted(comports()):
            print(' ')
            print(hwid)
            print("{}: {} [{}]".format(port, desc, hwid))
            if '2341:0043' in hwid:
                self.port_list.addItem(port)
            

    def toggle_connection(self,state):
        if state:
            self.connect()
        else:
            self.disconnect()


    def connect(self):
        # self.info_status.setText('opening port and initialising device. Please wait...')
        QtGui.QApplication.processEvents()
        self.opened.setChecked(True)
        portName = self.port_list.currentText()
        self.ser = serial.Serial(port=portName, baudrate=115200, timeout=0.5)
        time.sleep(0.5)
        self.userinfo("Initializing grbl...")
        self.ser.write("\r\n\r\n")
        time.sleep(2)
        self.ser.flushInput()
        self.set_spindle_speed()


    def disconnect(self):
        self.opened.setChecked(False)
        #self.stop_event.set()
        self.ser.close()
        #self.readthread.join()
        #self.info_status.setText('not connected!')


    def serial_write(self, commandstring, read=True):
        self.serial_active = True
        self.userinfo(commandstring)
        cmd = '%s\r\n' % commandstring
        self.ser.write(cmd.encode())
        if read:
            time.sleep(0.1)
            self.serial_read()
        time.sleep(0.1)
        self.serial_active = False
        self.gui_get_state()


    def serial_read(self):
        while self.ser.in_waiting:
            result = self.ser.readline().decode().strip()
            self.userinfo(result)


    def respond_gui_command(self):
        commandstring = self.gui_command.text()
        self.gui_command.clear()
        self.serial_write(commandstring)
        

    def unlock(self):
        self.serial_write('$X')
        self.motorlock_toggle()


    def motorlock_toggle(self):
        if self.motorlock_enable_cb.isChecked():
            self.serial_write('$1=255')
            self.serial_write('G91 G0 Y%.1f F%.0f' % (0.1, 1000))
            self.serial_write('G91 G0 Y%.1f F%.0f' % (-0.1, 1000))
            self.serial_write('G90')
        else:
            self.serial_write('$1=0')
            self.serial_write('G91 G0 Y%.1f F%.0f' % (0.1, 1000))
            self.serial_write('G91 G0 Y%.1f F%.0f' % (-0.1, 1000))
            self.serial_write('G90')

        
    def feed_hold(self):
        self.serial_write('!')


    def feed_resume(self):
        self.serial_write('~')


    def jog(self, what):
        stepmm = self.gui_jog_stepsize.value()
        feedrate = self.gui_jog_feedrate.value()
        print(what)
        if what == '-x':
            #self.serial_write('G91 G21 x-%.0f F%.0f' % (stepmm, feedrate))
            self.serial_write('G91 G0 x-%.1f F%.0f' % (stepmm, feedrate))
        if what == '+x':
            self.serial_write('G91 G0 x+%.1f F%.0f' % (stepmm, feedrate))
        if what == '-y':
            self.serial_write('G91 G0 y-%.1f F%.0f' % (stepmm, feedrate))
        if what == '+y':
            self.serial_write('G91 G0 y+%.1f F%.0f' % (stepmm, feedrate))

        if what == '-x -y':
            self.serial_write('G91 G0 x-%.1f y-%.1f F%.0f' % (stepmm, stepmm, feedrate))
        if what == '-x +y':
            self.serial_write('G91 G0 x-%.1f y+%.1f F%.0f' % (stepmm, stepmm, feedrate))
        if what == '+x -y':
            self.serial_write('G91 G0 x+%.1f y-%.1f F%.0f' % (stepmm, stepmm, feedrate))
        if what == '+x +y':
            self.serial_write('G91 G0 x+%.1f y+%.1f F%.0f' % (stepmm, stepmm, feedrate))

        self.serial_write('G90')


    def g0_go_to_position(self):
        x = self.gui_g1_xpos_mm.value()
        y = self.gui_g1_ypos_mm.value()
        f = self.gui_g1_feedrate.value()
        self.serial_write('G0 x%.1f y%.1f F%.0f' % (x, y, f)) 


    def g1_go_to_position(self):
        x = self.gui_g1_xpos_mm.value()
        y = self.gui_g1_ypos_mm.value()
        f = self.gui_g1_feedrate.value()
        self.serial_write('G1 x%.1f y%.1f F%.0f' % (x, y, f))


    def go_to_mcs_origin(self):
        f = self.gui_g1_feedrate.value()
        self.serial_write('G0 x%.1f y%.1f F%.0f' % (-self.g54_x, -self.g54_y, f)) 


    def go_to_wcs_origin(self):
        f = self.gui_g1_feedrate.value()
        self.serial_write('G0 x%.1f y%.1f F%.0f' % (0.0, 0.0, f)) 


    def gui_get_state(self):
        #self.serial_write('?')
        
        if self.online and not self.serial_active and not self.gcode_stream_running:
            try:
                cmd = '?\r\n'
                self.ser.write(cmd.encode())
                time.sleep(0.1)
                results = []
                while self.ser.in_waiting:
                    result = self.ser.readline().decode().strip()
                    results.append(result)
                # print(results)
                # state = results[0]
                self.gui_info_state1.setText(results[0])
                
                res1 = results[0].split(',')
                gpos_x = float(res1[4].split(':')[1])
                gpos_y = float(res1[5])
                
                cmd = '$#\r\n'
                self.ser.write(cmd.encode())
                time.sleep(0.1)
                results = []
                while self.ser.in_waiting:
                    result = self.ser.readline().decode().strip()
                    results.append(result)
                #print(results)
                self.gui_info_state2.setText(results[0])
        
                g54_x = float(results[0].split(',')[0].split(':')[1])
                g54_y = float(results[0].split(',')[1])
        
                self.gui_info_mcs_x.setText('MCS x = %.1f mm' % gpos_x)
                self.gui_info_mcs_y.setText('MCS y = %.1f mm' % gpos_y)
                self.gui_info_wcs_x.setText('WCS x = %.1f mm' % (gpos_x - g54_x))
                self.gui_info_wcs_y.setText('WCS y = %.1f mm' % (gpos_y - g54_y))
                self.gpos_x = gpos_x
                self.gpos_y = gpos_y
                self.g54_x = g54_x
                self.g54_y = g54_y
                
            except:
                print('read failed...')


    def gui_set_mcs_zero(self):
        self.userinfo('todo...')
        #@self.serial_write('G10 L20 P1 X0 Y0 Z0')
        #time.sleep(0.1)
        #self.gui_get_state()

    def gui_set_wcs_zero(self):
        self.serial_write('G10 L20 P1 X0 Y0 Z0')
        #time.sleep(0.1)
        #self.gui_get_state()


    def set_spindle_speed(self):
        spd = int(self.gui_spindlespeed.value())
        self.serial_write('S%i' % spd)


    def set_spindle_on(self):
        spd = int(self.gui_spindlespeed.value())
        self.serial_write('M03 S%0.f' % spd)
        

    def set_spindle_off(self):
        self.serial_write('M05')


    def gui_spindle_enable_cb_clicked(self):
        if self.gui_spindle_enable_cb.isChecked():
            # self.set_spindle_speed()
            self.set_spindle_on()
        else:
            self.set_spindle_off()


    def gui_get_state_online_cb_clicked(self):
        if self.gui_get_state_online_cb.isChecked():
            self.get_state_timer.start(500)
        else:
            self.get_state_timer.stop()


    def gcode_load_file(self):
        fn = self.gcodefile_text.toPlainText()
        self.userinfo('opening file %s ...' % fn)
        with open(fn, 'r') as file:
            gcode_lines1 = file.readlines()
            
        Nlines = len(gcode_lines1)
        
        self.gcode_lines = gcode_lines1
        
        for n, line in enumerate(gcode_lines1):
            # print(line.strip())
            ix = line.find(';')
            if ix:
                line1 = line[0:ix].upper()
            else:
                line1 = line.upper()
            # l1 = re.sub(';|\(.*?\)','',line).upper() # Strip comments/spaces/new line and capitalize
            # print(line1)
            self.gcode_lines[n] = line1
            
        # self.gcodefile_id.close()
        self.userinfo('%i G-code file lines read.' % Nlines)
        self.gcode_plot()


    def gcode_plot(self):
        self.gcode_coordinates = [[0], [0], [0]]

        for n, line in enumerate(self.gcode_lines):
            # l1 = line[0:line.find(';')].split()
            #print(line)
            #l1 = re.sub('|\(.*?\)','',line).upper() # Strip comments/spaces/new line and capitalize
            #print(l1)

            # print('%s\n%s\n' % (line.strip(), l1))
            l1 = line.split()
            
            if l1:

                if l1[0] == 'G00' or l1[0] == 'G0' or l1[0] == 'G01' or l1[0] == 'G1':
                    
                    x = y = None
                    for l11 in l1:
                        if l11.find('X') >= 0:
                            x = float(l11[1:])
                        if l11.find('Y') >= 0:
                            y = float(l11[1:])
            
                    if x is not None or y is not None:        
                        self.gcode_coordinates[0].append(x)
                        self.gcode_coordinates[1].append(y)
                
                        if l1[0] == 'G00' or l1[0] == 'G0':
                            self.gcode_coordinates[2].append(0)
                        if l1[0] == 'G01' or l1[0] == 'G1':
                            self.gcode_coordinates[2].append(1)
        
        for n in range(2):
            for m, c in enumerate(self.gcode_coordinates[n]):
                if c == None:
                    self.gcode_coordinates[n][m] = self.gcode_coordinates[n][m-1]
            
        # print(np.array(self.gcode_coordinates).transpose())
        # print(self.gcode_coordinates[1])
        # print(self.gcode_coordinates[2])
        self.plt_gcode.setData(x=self.gcode_coordinates[0], y=self.gcode_coordinates[1])


    def gcode_stream_start(self):
        self.userinfo('starting G-Code steam...')
        self.gcode_stream_running = True
        # self.gcode_stream_stopcommand = False

        #fn = self.gcodefile_text.toPlainText()
        #self.userinfo('opening file %s ...' % fn)
        #self.gcodefile_id = open(fn, 'r')
        #lines = self.gcodefile_id.readlines()
        
        self.gcode_load_file()
        Nlines = len(self.gcode_lines)
        #self.gcodefile_id.close()
        self.userinfo('%i G-code lines to send' % Nlines)
        
        l_count = 0
        g_count = 0
        c_line = []
        verbose = False
        RX_BUFFER_SIZE = 128

        now = pyqtgtime()
        self.ETAtimer_last = now
        self.ETAtimer_start = now
        # self.streamglobalcounter = 0
        
        for n, line in enumerate(self.gcode_lines):
            # print(line)
            #self.userinfo(line.strip())


            l_count += 1  # Iterate line counter
            # l_block = re.sub('\s|\(.*?\)','',line).upper() # Strip comments/spaces/new line and capitalize
            #l_block = re.sub('|\(.*?\)','',line).upper() # Strip comments/spaces/new line and capitalize
            l_block = line.strip()
            #print(l_block)
            #l_block = l_block[0:l_block.find(';')]
            self.userinfo(l_block)
            
            c_line.append(len(l_block)+1)  # Track number of characters in grbl serial read buffer
            grbl_out = '' 
            while sum(c_line) >= RX_BUFFER_SIZE-1 | self.ser.inWaiting():
                # out_temp = self.ser.readline().strip().decode()  # Wait for grbl response
                out_temp = self.ser.readline().decode().strip()
                # print("  Debug1: ", out_temp)
                if out_temp.find('ok') < 0 and out_temp.find('error') < 0 :
                    #print("  Debug: ", out_temp)  # Debug response
                    self.userinfo("Debug: " + out_temp)  # Debug response
                else :
                    grbl_out += out_temp;
                    g_count += 1 # Iterate g-code counter
                    grbl_out += str(g_count);  # Add line finished indicator
                    del c_line[0]  # Delete the block character count corresponding to the last 'ok'
                QtGui.QApplication.processEvents()

            if verbose: print("SND: " + str(l_count) + " : " + l_block,)
            # cmd = l_block + '\n'
            # cmd = '%s\r\n' % l_block
            cmd = '%s\n' % l_block
            self.ser.write(cmd.encode())  # Send g-code block to grbl
            # self.ser.write(l_block + '\n') # Send g-code block to grbl
            if verbose: print("BUF:",str(sum(c_line)),"REC:", grbl_out)
            self.userinfo(grbl_out)

            if not self.gcode_stream_running:
                break                

            if n % 10 == 0 or n+1 == Nlines:
                self.gcode_stream_progressbar.setValue((n+1)/Nlines*100)
                
                now = pyqtgtime()
                Dt0 = now - self.ETAtimer_start
                eta = Dt0/(n+1) * (Nlines-n)
                self.gui_eta_info.setText('line %i/%i, eta: %.0fh, %.0fm, %.0fs, runtime: %.0fh, %.0fm, %.0fs' %
                                               (n+1, Nlines, sec2HMS(eta)[0], sec2HMS(eta)[1], sec2HMS(eta)[2], sec2HMS(Dt0)[0], sec2HMS(Dt0)[1], sec2HMS(Dt0)[2] ) )
                
                QtGui.QApplication.processEvents()

        self.userinfo('G-Code steaming finished!')
        self._gcode_stream_stop_do()


    def gcode_stream_stop(self):
        self.userinfo('stopping G-Code steam!')
        self._gcode_stream_stop_do()


    def _gcode_stream_stop_do(self):
        self.gcode_stream_running = False
        # self.gcode_stream_stopcommand  = True


    def _browse_gcodefile(self):
        file = QtGui.QFileDialog.getOpenFileName(directory=self.gcodefile_text.toPlainText())
        print(file)
        print(file[0])
        self.gcodefile_text.setText(file[0])

    @property
    def online(self):
        isonline = False
        try:
            isonline = self.ser.isOpen()
        except:
            isonline = False
                
        return isonline


    def closeEvent(self, event):
        """Close program."""
        self.userinfo("closing GUI...")
        try:
            self.userinfo('closiung serial')
            self.ser.close()
        except:
            print("cannot close serial")
        print("bye bye...")
        

def main():
    """The main."""
    app = QtGui.QApplication(sys.argv)
    ex = vplottercontroller()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
