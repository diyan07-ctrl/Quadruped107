#pragma once
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <string>
#include <cassert>
#include <iostream>
#include <algorithm>
#define __attribute__(x)
#define HIGH 1
#define LOW 0
#define INPUT 0
#define OUTPUT 1
#define CHANGE 2
#define _BV(x) (1<<(x))
#define WDRF 3
struct __FlashStringHelper {};
#define F(s) reinterpret_cast<const __FlashStringHelper*>(s)
static uint8_t MCUSR=0;
static uint32_t fakeUs=0;
static uint8_t pins[20]={}, modes[20]={};
static bool wdtEnabled=false;
static unsigned watchdogServices=0;
inline uint32_t micros() { return fakeUs; }
inline uint32_t millis() { return fakeUs/1000; }
inline void delay(unsigned long ms) { fakeUs+=ms*1000; }
inline void digitalWrite(uint8_t pin,uint8_t state) { pins[pin]=state; }
inline int digitalRead(uint8_t pin) { return pins[pin]; }
inline void pinMode(uint8_t pin,uint8_t mode) { modes[pin]=mode; }
inline int digitalPinToInterrupt(int pin) { return pin; }
inline void attachInterrupt(int,void (*)(),int) {}
class FakeSerial {
public:
  std::string input, output;
  int capacity=64;
  void begin(long) {}
  int available() { return input.size(); }
  int availableForWrite() { return capacity; }
  char read() { char c=input[0]; input.erase(0,1); return c; }
  void print(const char *s) { output+=s; }
  void print(const __FlashStringHelper *s) { output+=reinterpret_cast<const char*>(s); }
  void print(char c) { output+=c; }
  template<class T> void println(T value) { print(value); output+='\n'; }
  size_t write(const uint8_t *data,size_t length) { output.append(reinterpret_cast<const char*>(data),length); return length; }
};
static FakeSerial Serial;
