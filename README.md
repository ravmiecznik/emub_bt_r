# emub_bt_r

## EMU_BT_R V2.3

https://www.youtube.com/watch?v=0i5L0DQhbt8

https://www.youtube.com/watch?v=bxWkzQrnqo4

https://github.com/ravmiecznik/atm128_bootloader_v3
```
    23.02.2020: Test suite at system level added. Test of: upload, download, digidiag transmission.
                TODO Test Suite:
                    Create an html report for test execution
                    Collect and archive test artifacts after test execution
                    Define different test suites with different level of detail
                    Add Live emulation test
                TODO EMUBT:
                    Add an option to override default digiframes configuration
                    Still working on Huffman compression (new version should be created)
    17.02.2020: New bootloader3/reflasher: https://github.com/ravmiecznik/atm128_bootloader_v3
    23.11.2019: EXE file is created according to operating system name.
				Support for WIN7
				Application estimates average response time from BT to set optimal maximum timeouts
				Display location of new windows updated
    11.11.2019: New branch. Reflash procedure fixed, first version of data monitoring and configuration available.
                Save button ranamed to UPLOAD (more resonable name)
    29.09.2019: Full and independent bi-directional communication. APP to BOARD message uses message with header (id, context, len, crc),
                BOARD to APP message uses tail which is attached to message (id, context, len). Rx messages are stored in rx buffer and are
                filtered after its id and context. It allows to much more flexible transmission schemes like receiving random data (digifant
                diagnostic frames, board cpuload, random text and of cource ack/nacks and transmitted data frames)
                New version also implements first approach for digifant diagnostics: reception and storage of digifant diagnostic frames.
                Target goal is to display full logging with gauges and LCD displays. 
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
    
    REFLASHER/BOOTLOADER3
    -new bootloader3 support with new reflasher applicaton
    -new booloader3 implements different approach for ack/nack handling
    -full control of transmission is on EMU_BT appliaction, it decides what to retransmit and it counts timeouts
    -EMU_BT board role is to send ack/nack, does not send anything if packet not received
    
    #TODO:
    -Bin file viewer to be added to see commited changes by EMULATION procedure
    -implement gauge/lcd displays for digifant diagnostics
    
    Fixed:
    -occassional crashes on read bank name procedures, read/send binary data
    -all additional windows are displayed on top of main window
```