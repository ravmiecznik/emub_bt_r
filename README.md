# emub_bt_r

EMU_BT_R V2.0

https://www.youtube.com/watch?v=0i5L0DQhbt8

https://www.youtube.com/watch?v=bxWkzQrnqo4

    23.07.2019: Optimized timings, num of retx, tested on Win10/LINUX
    10.09.2019: Version 2.0 works with EMUBT.avr V >= 2.0
                Messaging scheme change:
                    -message sender: add new field to msg header: context_id
                    -implememnt general message receiver according to new message sender from EMUBT board
                    -new msg sender from the board will send a message body and message tail in the end with: msg_id, context_id, crc, msg_len
                    -with msg_tail it will be possible to read message body from rx_buffer and put it to message storage (dictionary ?)
                    -it will be possible to read message from storage by its context_id (msg_storage.pop(context_id))

First working version features:

    Control:
    -autodiscovery of EMU_BT device
    -reflash procedure of EMU_BT device (with internal bootloader)
    -config window (needs to be improved)

    Emulation:
    -EMULATE: tracks changes in selected binary file, if there is a change it is uploaded to SRAM memory of EMU_BT, changes are working until EMU_BT restart, volataile change
    -SAVE: stores current binary file in EMU_BT flash memory (permanent save)
    -READ_BANK/READ_SRAM: downloads content of current flash bank or SRAM memory to file
    -auto_open checkbox: if selected it will open downloaded content in specified bin/hex editor
    -reload sram on sava checkbox: if checked it will trigger reload of sram memory after SAVE operation

    Banks:
    -bank1/2/3 - select flash bank to load to SRAM
    -text edit box: enter name for selected bank, this name is stored in EMU_BT device
    -auto download: not yet implemented

    BIN FILE:
    -list combo box: contains history of selected binary files
    -OPEN: open current bin file (the top one in combo box) and open in specified bin/hex editor
    -'...' browse button: select binary file with file browser
    -BIN FILE panel supports also drag-drop operation to drop binary file
    -check if binary file is valid 27c256 image, if not selection will be rejected

    CONSOLE:
    -communication window 
    -supports text selection
    -user can select text, it is autamatically pasted in command line below, command can be executed with mouse-wheel-press
    -HLP: display command line supported commands for EMU_BT device
    -RST: reset EMU_BT

    BLANK PANEL BELOW:
    -this panel displays some tips for actually pointed by mouse button/window/checkbox

	17/08/2019:
	-check if digidiag resumed
	-refactored and improved procedures: read bin data from emu, save bin data to emu
	-in DBG: stdout, stderr to file for release version
	-first version of digidiag implemented in EMUBT
    
    #TODO:
    -Bin file viewer to be added to see commited changes by EMULATION procedure
    -call tracker must be fixed: this is not big issue, just for debugging purposes
	-display window for digidiag
