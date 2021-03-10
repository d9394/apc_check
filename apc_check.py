#!/usr/bin/python2.7
#coding=utf8

import serial
import csv
import time
import subprocess

PORT = '/dev/ttyUSB1'
BAUDRATE = 2400
SLEEP_SECONDS = 60
SHUTDOWN_DELAY_TIMES = 3   #TOTAL DELAY TIME = SHUTDOWN_DELAY_TIMES * SLEEP_SECONDS

class APCSerial(object):
	Input_vol=0.0
	Output_vol=0.0
	Fault_vol=0.0
	Output_Frequency=0.0
	Battery_vol=0.0
	Temperature=0.0
	Load_percentage=0
	Utility_Fail=''
	Battery_Low=''
	Boost_Buck_Mode=''
	Ups_Fail=''
	Ups_Line_Interactive=''
	Ups_Self_Test=''
	Ups_Shutdown=''
	Ups_Beeper=''
	__Read_Status_OK=''
	Ups_Status = ""
	
	def __init__(self, port, baudrate=2400):
		# todo: check that port exists & init errors
		self.serial = serial.Serial(port, baudrate, timeout=1, rtscts=1)
		self.serial.write('M\r')
		mode = self.serial.readline()
		# todo: test init in Smart mode (UPS returns 'V\r')
		#print(u"APC mode %s" % mode)

	def _read_ups(self, command):
		self.serial.write(command)
		response = self.serial.readline()
		return response
		
	def bettery_test(self):
		self._read_ups('T\r')
		#no response require
		
	def shutdown_ups(self, shutdown_delay=".2", restore_wait="0000"):
		self._read_ups('S' + shutdown_delay + 'R' & restore_wait + '\r')
		#no response require
		
	def cancel_shutdown(self):
		self._read_ups('C\r')
		#no response require
		
	def toggle_beep(self):
		self._read_ups('Q\r')
		#no response require
		
	def read_status(self):
		__status = self._read_ups('QS\r')
		#UPS return '(220.2 220.2 220.2 015 50.0 13.5 --.- 00001001\r'
		self.Ups_Status=__status.replace('\r', '').replace('(','').split(' ')
		if len(self.Ups_Status)==8 :
			self.Input_vol = float(self.Ups_Status[0])
			self.Output_vol = float(self.Ups_Status[2])
			self.Fault_vol = float(self.Ups_Status[1])
			self.Load_percentage = int(self.Ups_Status[3])
			self.Output_Frequency = float(self.Ups_Status[4])
			self.Battery_vol = float(self.Ups_Status[5])
			try:
				self.Temperature = float(self.Ups_Status[6])
			except :
				self.Temperature = 0.0
			self.Utility_Fail='功能正常' if self.Ups_Status[7][0:1] else '功能失败'
			self.Battery_Low='电池电压正常' if self.Ups_Status[7][1:2] else '电池电压低'
			self.Boost_Buck_Mode='非升降压模式' if self.Ups_Status[7][2:3] else '非升降压模式'
			self.Ups_Fail='UPS正常' if self.Ups_Status[7][3:4] else 'UPS故障'
			self.Ups_Line_Interactive='UPS直通模式' if self.Ups_Status[7][4:5] else 'UPS在线互动模式'
			self.Ups_Self_Test='UPS非自检' if self.Ups_Status[7][5:6] else 'UPS自检进程'
			self.Ups_Shutdown='UPS非关机进程' if self.Ups_Status[7][6:7] else 'UPS关机进程'
			self.Ups_Beeper='静音' if self.Ups_Status[7][7:8] else '蜂鸣器'
			__Read_Status_OK = True
		else:
			__Read_Status_OK = False
		return __Read_Status_OK
		 
	def serial_close(self):
		self.serial.close()

def send_message(m):
	subprocess.call('wget -O- "http://127.0.0.1:80/?usr=xxx&msg=' + m + '" > /dev/null',shell=True)
  #only test for send message to me

def main():
	apcserial = APCSerial(PORT, BAUDRATE)
	fail_count = SHUTDOWN_DELAY_TIMES
	a = 1
	while a:
		if apcserial.read_status() :
			print( '%s，输入%sV' % (apcserial.Ups_Fail, apcserial.Input_vol))
			print( '%s，电池%sV' % (apcserial.Battery_Low,apcserial.Battery_vol))
			print( '%s，负载%d%%' % (apcserial.Utility_Fail,apcserial.Load_percentage))
			print( '%s，输出%sV' % (apcserial.Ups_Line_Interactive,apcserial.Output_vol))
			print( '%s，失效%sV' % (apcserial.Boost_Buck_Mode,apcserial.Fault_vol))
			if int(apcserial.Input_vol) < 100 and int(apcserial.Fault_vol ) < 100 :
				send_message("第%d次输入电压异常(%sV/%sV)" % (int(SHUTDOWN_DELAY_TIMES - fail_count + 1), apcserial.Input_vol, apcserial.Fault_vol))
				print( '无输入电压错误' )
				print( '准备关机' )
				fail_count -= 1
				if fail_count == 0 :
					print('要求关机')
					send_message("进入关机程序")
					subprocess.call('shutdown -h 1 &',shell=True)
					sys.exit(1)
			else :
				if fail_count < SHUTDOWN_DELAY_TIMES :
					send_message("输入电压恢复正常%s" % apcserial.Input_vol)
					fail_count = SHUTDOWN_DELAY_TIMES
			if int(apcserial.Battery_vol) < 10 :
				send_message("电池电压低%s" % apcserial.Battery_vol)
		else :
			print(u'读取UPS数据错误')
		time.sleep(SLEEP_SECONDS)
		#a = 0
	apcserial.serial_close()
	
if __name__ == '__main__':
	main()
