# %% imports
import time
import serial
from serial.tools.list_ports import comports


# %% list all com ports
# for port, desc, hwid in sorted(comports()):
#     print(' ')
#     print(hwid)
#     print("{}: {} [{}]".format(port, desc, hwid))
    

# %%
grbl_ports_hwid = []
grbl_ports_port = []

for port, desc, hwid in sorted(comports()):
    print(' ')
    print(hwid)
    print("{}: {} [{}]".format(port, desc, hwid))
    if '2341:0043' in hwid:
        print('found GRBL')
        grbl_ports_hwid.append(hwid)
        grbl_ports_port.append(port)

print('found GRBL devices:')
print(grbl_ports_hwid, grbl_ports_port)



# %%
# portName = '/dev/ttyACM0'
portName = grbl_ports_port[0]

ser = serial.Serial(port=portName, baudrate=115200, timeout=0.5)

# %% try read

# Wake up grbl
print("Initializing grbl...")
ser.write(b"\r\n\r\n")

# Wait for grbl to initialize and flush startup text in serial input
time.sleep(1)
ser.flushInput()



# %%
def ser_read(ser):
    while ser.in_waiting:
        result = ser.readline().decode().strip()
        print(result)


def ser_write(ser, commandstring):
    cmd = '%s\r\n' % commandstring
    ser.write(cmd.encode())
    time.sleep(0.1)
    ser_read(ser)

    

# %%
ser_write(ser, '$#')

# %%
ser_write(ser, 'g1 x5 y0 f1000')

# %%
ser_write(ser, '$I')


# %%
ser_write(ser, '$G')

# %%
ser_write(ser, '?')

# %% resume
ser_write(ser, '~')

# %%feed hold
ser_write(ser, '$!')

# %% unlock
ser_write(ser, '$X')

# %% jogging
ser_write(ser, 'G91 G0 x10')

# %% spindle / servo to position
ser_write(ser, 'M3 S0')

# %% spindle / servo park
ser_write(ser, 'M5')


# %%
cmd = '?\r\n'
ser.write(cmd.encode())
time.sleep(0.1)
results = []
while ser.in_waiting:
    results.append(ser.readline().decode().strip())

print(results)
res1 = results[0].split(',')
print(res1)

gpos_x = float(res1[4].split(':')[1])
gpos_y = float(res1[5])

# %%
cmd = '$#\r\n'
ser.write(cmd.encode())
time.sleep(0.1)
results = []
while ser.in_waiting:
    results.append(ser.readline().decode().strip())

print(results)

g54_x = float(results[0].split(',')[0].split(':')[1])
g54_y = float(results[0].split(',')[1])


# %% gcode reading testing:
import os
import numpy as np
import matplotlib.pyplot as plt

fn = os.path.join(os.path.expanduser('~'), 'test.gcode')
with open(fn, 'r') as file:
    gcode_lines = file.readlines()

# print(gcode_lines)
#gcode_coordinates_g0_x = [0]
#gcode_coordinates_g0_y = [0]

# gcode_coordinates_g0 = [[0], [0]]
# gcode_coordinates_g1 = [[], [], []]

gcode_coordinates = [[0], [0], [0]]


# def extract_xy(txt):
#     x = None
#     y = None

#     for txt1 in txt:

#         if txt1.find('X') >= 0:
#             x = float(txt1[1:-1])
            
#         if txt1.find('Y') >= 0:
#             y = float(txt1[1:-1])
            
#     return x, y


for n, line in enumerate(gcode_lines):
    l1 = line[0:line.find(';')].split()
    
    if l1:
        print('%s\n%s' % (line.strip(), l1))
    
        if l1[0] == 'G00' or l1[0] == 'G0' or l1[0] == 'G01' or l1[0] == 'G1':

            x = y = None
    
            for l11 in l1:
    
                if l11.find('X') >= 0:
                    x = float(l11[1:])
                    print('x=%.2f\n' % x)
                    
                if l11.find('Y') >= 0:
                    y = float(l11[1:])
                    print('y=%.2f\n' % y)

            if x is not None or y is not None:
                gcode_coordinates[0].append(x)
                gcode_coordinates[1].append(y)
    
                if l1[0] == 'G00' or l1[0] == 'G0':
                    gcode_coordinates[2].append(0)
                if l1[0] == 'G01' or l1[0] == 'G1':
                    gcode_coordinates[2].append(1)
    
            
    

    # if l1[0] == 'G00' or l1[0] == 'G0':
    #     x, y = extract_xy(l1)
    #     print(x, y)
    #     gcode_coordinates_g0[0].append(x)
    #     gcode_coordinates_g0[1].append(y)

    # if l1[0] == 'G01' or l1[0] == 'G1':
    #     x, y = extract_xy(l1)
    #     print(x, y)    
    #     gcode_coordinates_g1[0].append(x)
    #     gcode_coordinates_g1[1].append(y)

for n in range(2):
    for m, x in enumerate(gcode_coordinates[n]):
        if x == None:
            gcode_coordinates[n][m] = gcode_coordinates[n][m-1]



# for n in range(2):
#     for m, x in enumerate(gcode_coordinates_g0[n]):
#         if x == None:
#             gcode_coordinates_g0[n][m] = gcode_coordinates_g0[n][m-1]
    
# for n in range(2):
#     for m, x in enumerate(gcode_coordinates_g1[n]):
#         if x == None:
#             gcode_coordinates_g1[n][m] = gcode_coordinates_g1[n][m-1]


# print(gcode_coordinates_g0[0])
# print(gcode_coordinates_g0[1])


# print(gcode_coordinates_g1[0])
# print(gcode_coordinates_g1[1])


#print(gcode_coordinates[0])
#print(gcode_coordinates[1])

print(np.array(gcode_coordinates).transpose())


if False:
    fig = plt.figure(num=111, figsize=(15,18), dpi=200)
    fig.clear()
    ax = fig.subplots(1, 1)
    # ax.plot(gcode_coordinates_g0[0], gcode_coordinates_g0[1], label='g0')
    # ax.plot(gcode_coordinates_g1[0], gcode_coordinates_g1[1], label='g1')
    ax.plot(gcode_coordinates[0], gcode_coordinates[1], label='g0+g1')
    fig.show()
    ax.legend()



            
            
    

