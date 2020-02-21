EMUBT V2

Refactor of message sender.
EMUBT V2 works only with EMUBT.py >= V2.0

------------TAG: emubt_V2.2_191512------------------------------------------------------------------------------------------------------------------------------------------

15.12.2019: -Dynamic injection of Digidiag program works for 1 and 3 map digifant program
            -Detection if program is 1 or 3 map version and apply appopriate digidiag frames according to it
            -Bug fixed: find_free_space function in DigidiagPatcher did overwrite last RTS instruction causing transmission errors

TODO:       -Add missing digidiag frames for 3 map digifant program version
            -Rework bootloader so it can receive data in more robust way, apply similar approach as it is done for Banks writing
            -Apply compression for binary files transmission
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------

-----------TAG: emubt_V2.2_192411-------------------------------------------------------------------------------------------------------------------------------------------

TODO:       Dynamic digidag patch works for 1MAP binary. Add frames id to load to SRAM, add verification if it is 1MAP or 3MAP program: both differs in RAM organization and 
            requires different DIGIFRAMES vectors. Also placement of DIGIDIAG routine may be different.
            Add Digidiag code hiding when board is not in ECU

24.11.2019: New branch will cover dynamic digidiag program injection and protection, it should be able to handle most of available Digifant binaries.
            The concept:
            -identify interrupt vectors addresses which are stored in the end of IMAGE
            -using interrupt adresses inject/modify the binary accordingly
            -create an algorithm to dynamically set jumps addresses
11.11.2019: Digidiag program protected. In Digifant image replace whole digidag program with "rti" (0x3B) instruction.
            Whole program is stored inside Emubt.hex, if eeprom image contains "digidiag" string at address 0x0 it will write 
            digidiag program into sram.

Refactoring concept:
-modify message receiver with context_id field in msg header
-response for given message will contain context_id
-response is no plain text anymore: it will contain header and body
-due to memory limitation on atmega sending message works as follows:
    *send message body
    *when message body is being transmitted calculate its crc and length
    *send "msg_tail" after body was send {msg_id, context_id, crc}
    *<msg_body><msg_tail>
-EMUBT.py should search for msg_tail in rx_buffer, if it is found extract message body with given len: msg_body index=index(msg_tail) - msg.len

