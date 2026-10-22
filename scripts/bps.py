#!/usr/bin/env python3
"""Small BPS writer/applier with source, target, and patch CRC verification.

Format: https://github.com/Sir-Walrus/Flips/blob/master/bps_spec.md
The writer knows the source dump has a 512-byte copier header.
"""
import argparse
from pathlib import Path
import struct
import zlib

def number(n):
    out=bytearray()
    while True:
        x=n&127;n>>=7
        if not n:
            out.append(x|128);return out
        out.append(x);n-=1

def signed(n):return number((abs(n)<<1)|(n<0))

def create(source,target,header=512,metadata=b'Stage 1 skyline smooth-parallax prototype; other stages unchanged.'):
    out=bytearray(b'BPS1')+number(len(source))+number(len(target))+number(len(metadata))+metadata
    pos=0;src_cursor=0;dst_cursor=0
    while pos<len(target):
        end=pos
        while end<len(target) and end+header<len(source) and target[end]==source[end+header]:end+=1
        if end-pos>=4:
            out+=number(((end-pos-1)<<2)|2)+signed(pos+header-src_cursor)
            src_cursor=end+header;pos=end;continue
        end=pos+1
        while end<len(target) and target[end]==target[pos]:end+=1
        if end-pos>=16:
            out+=number(1)+target[pos:pos+1]
            out+=number(((end-pos-2)<<2)|3)+signed(pos-dst_cursor)
            dst_cursor=end-1;pos=end;continue
        end=pos+1
        while end<len(target):
            if end+header+4<=len(source) and target[end:end+4]==source[end+header:end+header+4]:break
            if end+16<=len(target) and target[end:end+16]==target[end:end+1]*16:break
            end+=1
        out+=number(((end-pos-1)<<2)|1)+target[pos:end];pos=end
    out+=struct.pack('<II',zlib.crc32(source),zlib.crc32(target))
    out+=struct.pack('<I',zlib.crc32(out))
    return bytes(out)

def apply(source,patch):
    if patch[:4]!=b'BPS1' or len(patch)<16:raise ValueError('Invalid BPS file')
    src_crc,dst_crc,patch_crc=struct.unpack('<III',patch[-12:])
    if zlib.crc32(patch[:-4])!=patch_crc:raise ValueError('Patch CRC mismatch')
    if zlib.crc32(source)!=src_crc:raise ValueError('Source CRC mismatch: wrong ROM/header')
    pos=4
    def read_number():
        nonlocal pos
        value=0;shift=1
        while True:
            if pos>=len(patch)-12:raise ValueError('Truncated BPS number')
            x=patch[pos];pos+=1;value+=(x&127)*shift
            if x&128:return value
            shift<<=7;value+=shift
    if read_number()!=len(source):raise ValueError('Source size mismatch')
    size=read_number();meta_size=read_number();pos+=meta_size
    result=bytearray();src_cursor=0;dst_cursor=0
    while pos<len(patch)-12:
        action=read_number();length=(action>>2)+1;mode=action&3
        if len(result)+length>size:raise ValueError('Target length overflow')
        if mode==0:
            offset=len(result)
            if offset+length>len(source):raise ValueError('SourceRead bounds')
            result+=source[offset:offset+length]
        elif mode==1:
            if pos+length>len(patch)-12:raise ValueError('TargetRead bounds')
            result+=patch[pos:pos+length];pos+=length
        else:
            delta=read_number();delta=(delta>>1)*(-1 if delta&1 else 1)
            if mode==2:
                src_cursor+=delta
                if src_cursor<0 or src_cursor+length>len(source):raise ValueError('SourceCopy bounds')
                result+=source[src_cursor:src_cursor+length];src_cursor+=length
            else:
                dst_cursor+=delta
                if dst_cursor<0 or dst_cursor>=len(result):raise ValueError('TargetCopy bounds')
                for _ in range(length):result.append(result[dst_cursor]);dst_cursor+=1
    if len(result)!=size or zlib.crc32(result)!=dst_crc:raise ValueError('Target size/CRC mismatch')
    return bytes(result)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['create','apply'])
    p.add_argument('source',type=Path);p.add_argument('second',type=Path);p.add_argument('output',type=Path)
    args=p.parse_args();source=args.source.read_bytes();second=args.second.read_bytes()
    if args.mode=='create':
        data=create(source,second)
        if apply(source,data)!=second:raise RuntimeError('BPS round-trip failed')
    else:data=apply(source,second)
    args.output.write_bytes(data)
    print(f'{args.output}: {len(data)} bytes; checksums verified')
