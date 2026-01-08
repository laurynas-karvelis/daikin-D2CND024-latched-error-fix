#!/usr/bin/env python3

import serial
import sys
import time
import argparse

DEFAULT_PORT = "/dev/cu.usbserial-1130"
BAUD = 115200
PAGE_SIZE = 32
EEPROM_SIZE = 8192

def connect(port):
    try:
        ser = serial.Serial(port, BAUD, timeout=2)
        time.sleep(2)
        ser.reset_input_buffer()
        return ser
    except serial.SerialException as e:
        print(f"Error: Cannot open port {port}: {e}")
        sys.exit(1)

def send_cmd(ser, cmd):
    ser.write((cmd + "\n").encode())
    return ser.readline().decode().strip()

def read_eeprom(port, output_file):
    print(f"Connecting to {port}...")
    ser = connect(port)
    
    resp = send_cmd(ser, "PING")
    if resp != "PONG":
        print(f"Device not responding: {resp}")
        sys.exit(1)
    print("Device connected")
    
    print("\n--- Reading ---")
    data = bytearray()
    addr = 0
    
    while addr < EEPROM_SIZE:
        chunk_size = min(PAGE_SIZE, EEPROM_SIZE - addr)
        chunk, err = read_page(ser, addr, chunk_size)
        
        if err:
            print(f"\nRead error at 0x{addr:04X}: {err}")
            sys.exit(1)
        
        data.extend(chunk)
        pct = (addr + chunk_size) * 100 // EEPROM_SIZE
        print(f"\r  0x{addr:04X} / 0x{EEPROM_SIZE:04X} ({pct}%)", end="", flush=True)
        addr += chunk_size
    
    ser.close()
    
    with open(output_file, "wb") as f:
        f.write(data)
    
    print(f"\n\nDone! {output_file} is {len(data)} bytes")
    
    if len(data) == EEPROM_SIZE:
        print("✓ Size correct!")
    else:
        print(f"⚠ Expected {EEPROM_SIZE} bytes")

def write_page(ser, addr, data):
    cmd = f"WRITE {addr} {len(data)}"
    resp = send_cmd(ser, cmd)
    if resp != "OK":
        return False, f"Write setup failed: {resp}"
    ser.write(bytes(data))
    resp = ser.readline().decode().strip()
    if resp != "DONE":
        return False, f"Write failed: {resp}"
    return True, None

def read_page(ser, addr, length):
    cmd = f"READ {addr} {length}"
    ser.write((cmd + "\n").encode())
    resp = ser.readline().decode().strip()
    if not resp.startswith("DATA "):
        return None, f"Read failed: {resp}"
    hex_data = resp[5:]
    data = bytes.fromhex(hex_data)
    return data, None

def write_eeprom(port, input_file):
    with open(input_file, "rb") as f:
        data = f.read()
    
    if len(data) > EEPROM_SIZE:
        print(f"Error: File size {len(data)} exceeds EEPROM size {EEPROM_SIZE}")
        sys.exit(1)
    
    print(f"File: {input_file} ({len(data)} bytes)")
    print(f"Connecting to {port}...")
    
    ser = connect(port)
    
    resp = send_cmd(ser, "PING")
    if resp != "PONG":
        print(f"Device not responding: {resp}")
        sys.exit(1)
    print("Device connected")
    
    print("\n--- Writing ---")
    addr = 0
    while addr < len(data):
        chunk_size = min(PAGE_SIZE, len(data) - addr)
        chunk = data[addr:addr + chunk_size]
        
        ok, err = write_page(ser, addr, chunk)
        if not ok:
            print(f"\nWrite error at 0x{addr:04X}: {err}")
            sys.exit(1)
        
        pct = (addr + chunk_size) * 100 // len(data)
        print(f"\r  0x{addr:04X} / 0x{len(data):04X} ({pct}%)", end="", flush=True)
        addr += chunk_size
    
    print("\n\n--- Verifying ---")
    addr = 0
    errors = 0
    while addr < len(data):
        chunk_size = min(PAGE_SIZE, len(data) - addr)
        expected = data[addr:addr + chunk_size]
        
        actual, err = read_page(ser, addr, chunk_size)
        if err:
            print(f"\nRead error at 0x{addr:04X}: {err}")
            sys.exit(1)
        
        if actual != expected:
            errors += 1
            print(f"\n  Mismatch at 0x{addr:04X}:")
            print(f"    Expected: {expected.hex()}")
            print(f"    Got:      {actual.hex()}")
        
        pct = (addr + chunk_size) * 100 // len(data)
        print(f"\r  0x{addr:04X} / 0x{len(data):04X} ({pct}%)", end="", flush=True)
        addr += chunk_size
    
    ser.close()
    
    print("\n")
    if errors == 0:
        print("SUCCESS: Verification passed")
    else:
        print(f"FAILED: {errors} page(s) with errors")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Read/Write EEPROM NV24C64 via Arduino",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s read -o backup.bin
  %(prog)s read -o backup.bin -p /dev/ttyUSB0
  %(prog)s write -i modified.bin
  %(prog)s write -i modified.bin -p /dev/ttyUSB0
        """
    )
    
    parser.add_argument(
        "command",
        choices=["read", "write"],
        help="Operation to perform"
    )
    
    parser.add_argument(
        "-p", "--port",
        default=DEFAULT_PORT,
        help=f"Serial port (default: {DEFAULT_PORT})"
    )
    
    parser.add_argument(
        "-i", "--input",
        help="Input file for write operation"
    )
    
    parser.add_argument(
        "-o", "--output",
        help="Output file for read operation"
    )
    
    args = parser.parse_args()
    
    if args.command == "read":
        if not args.output:
            parser.error("read command requires -o/--output")
        read_eeprom(args.port, args.output)
    
    elif args.command == "write":
        if not args.input:
            parser.error("write command requires -i/--input")
        write_eeprom(args.port, args.input)

if __name__ == "__main__":
    main()
