

with open('C:\git\emub_bt_r\dump.bin', 'rb') as f1, open('dump.bin', 'rb') as f2:
    for i, j in enumerate(f1):
        print j,
