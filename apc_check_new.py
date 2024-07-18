#!/usr/bin/python3.8
#coding=utf8

import csv
from time import sleep, strftime, time
import os
import termios
import threading
import urllib.request
import urllib.parse

BAUDRATE = 2400
SLEEP_SECONDS = 60	#seconds
SHUTDOWN_DELAY_TIMES = 3   #TOTAL DELAY TIME = SHUTDOWN_DELAY_TIMES * SLEEP_SECONDS
DEBUG = False

class SerialPort:
	def __init__(self, port, baudrate, timeout=1):
		self.port = port
		self.baudrate = baudrate
		self.timeout = timeout
		self.fd = self.open_serial(port, baudrate)
		self.buffer = ""
		self.read_thread = threading.Thread(target=self.read_from_port)
		self.read_thread.daemon = True
		self.running = True

	def open_serial(self, port, baudrate):
		# 打开串口
		fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
		
		# 获取当前串口设置
		attrs = termios.tcgetattr(fd)

		# 设置串口波特率
		baudrate_attr = self.get_baudrate_attr(baudrate)
		if baudrate_attr is None:
			raise ValueError("Unsupported baudrate")
		
		attrs[4] = baudrate_attr  # 设置输出波特率
		attrs[5] = baudrate_attr  # 设置输入波特率

		# 设置串口参数: 8个数据位，无校验，1个停止位
		attrs[2] = (attrs[2] & ~termios.CSIZE) | termios.CS8  # 8位数据
		attrs[2] &= ~termios.PARENB  # 无校验
		attrs[2] &= ~termios.CSTOPB  # 1位停止位

		# 设置RTS/CTS硬件流控制
		attrs[2] |= termios.CRTSCTS

		# 应用新的串口设置
		termios.tcsetattr(fd, termios.TCSANOW, attrs)
		
		return fd

	def get_baudrate_attr(self, baudrate):
		baudrate_mapping = {
			2400: termios.B2400,
			9600: termios.B9600,
			19200: termios.B19200,
			115200: termios.B115200
		}
		return baudrate_mapping.get(baudrate, None)

	def write(self, data):
		os.write(self.fd, data.encode())

	def read_from_port(self):
		while self.running:
			data = self.read()
			if data:
				print("Received:", data)

	def read(self, size=100):
		end_time = time() + self.timeout
		while time() < end_time:
			try:
				data = os.read(self.fd, size)  # 从串口读取数据
				if data:
					return data.decode()
			except BlockingIOError:
				sleep(0.1)
		return ""

	def readline(self):
		end_time = time() + self.timeout
		while time() < end_time:
			data = self.read()
			if data:
				self.buffer += data
				if '\n' in self.buffer:
					line, self.buffer = self.buffer.split('\n', 1)
					return line + '\n'
			sleep(0.1)  # 避免忙等待
		return ""

	def start_reading(self):
		self.read_thread.start()

	def stop_reading(self):
		self.running = False
		self.read_thread.join()

	def close(self):
		self.stop_reading()
		os.close(self.fd)


class APCSerial:
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
		self.serial = SerialPort(port, baudrate)
		mode = self._read_ups('M\n')
		# todo: test init in Smart mode (UPS returns 'V\n')
		print( u"%s : PORT %s link APC mode %s" % (strftime("%Y%m%d-%H%M%S"), port, mode))

	def _read_ups(self, command):
		self.serial.write(command)
		response = self.serial.readline()
		#print('send %s , return %s' % (command, response))
		return response
		
	def bettery_test(self):
		self._read_ups('T\n')
		#no response require
		
	def shutdown_ups(self, shutdown_delay=".2", restore_wait="0000"):
		self._read_ups('S' + shutdown_delay + 'R' & restore_wait + '\n')
		#no response require
		
	def cancel_shutdown(self):
		self._read_ups('C\n')
		#no response require
		
	def toggle_beep(self):
		self._read_ups('Q\n')
		#no response require
		
	def read_status(self):
		__status = self._read_ups('QS\n')
		#UPS return '(220.2 220.2 220.2 015 50.0 13.5 --.- 00001001\n'
		self.Ups_Status=__status.replace('\n', '').replace('(','').split(' ')
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
	# 构建 URL
	url = f'http://127.0.0.1:8001/?usr=abc&from=UPS&msg=({strftime("%Y%m%d-%H%M%S")})\n{m}'
	encoded_url = urllib.parse.quote(url, safe='/:?=&')
	if DEBUG :
		print("Send message : %s" % url)
	try:
		with urllib.request.urlopen(encoded_url) as response:
			# 忽略响应内容
			pass
	except Exception as e:
		# 打印错误消息（如果有）
		print("%s 发送 %s 错误：%s" % (strftime("%Y%m%d-%H%M%S"), encoded_url, e))
	
def get_device_port():
	# 列出 /dev 目录中的所有文件
	all_files = os.listdir('/dev')
	# 过滤出符合 ttyUSB* 模式的文件
	usb_ports = [f'/dev/{file}' for file in all_files if file.startswith('ttyUSB')]
	return usb_ports

def main():
	for PORT in get_device_port():
	#	PORT = '/dev/ttyUSB0'
		try:
			apcserial = APCSerial(PORT, BAUDRATE)
			sleep(1)
			fail_count = SHUTDOWN_DELAY_TIMES
			notice_count = 0
			while notice_count >= 0 :
				if apcserial.read_status() :
					if int(apcserial.Input_vol) < 100 and int(apcserial.Fault_vol ) < 100 :
						send_message("第%d次输入电压异常(%sV/%sV)，电池%sV，负载%d%%" % (int(SHUTDOWN_DELAY_TIMES - fail_count + 1), apcserial.Input_vol, apcserial.Fault_vol, apcserial.Battery_vol, apcserial.Load_percentage))
						print( '无输入电压错误\n' )
						print( '准备关机\n' )
						fail_count -= 1
						if fail_count == 0 :
							print('要求关机')
							send_message("进入关机程序，电池电压%sV" % apcserial.Battery_vol)
							os.system('sudo shutdown now')
							#sys.exit(1)
					else :
						if fail_count < SHUTDOWN_DELAY_TIMES :
							send_message("输入电压恢复正常%s" % apcserial.Input_vol)
							fail_count = SHUTDOWN_DELAY_TIMES
					if int(apcserial.Battery_vol) < 10 :
						send_message("电池电压低%s" % apcserial.Battery_vol)
					if int(apcserial.Temperature) > 50 :
						send_message("设备温度异常%d" % apcserial.Temperature)
				else :
					print(u'读取UPS数据错误')
				if notice_count % 60 == 0 or DEBUG:
					msg = ('%s，输入%sV\n%s，电池%sV\n%s，负载%d%%\n%s，输出%sV\n%s，失效%sV\n，温度%d\n' % (apcserial.Ups_Fail, apcserial.Input_vol,apcserial.Battery_Low,apcserial.Battery_vol,apcserial.Utility_Fail,apcserial.Load_percentage,apcserial.Ups_Line_Interactive,apcserial.Output_vol,apcserial.Boost_Buck_Mode,apcserial.Fault_vol, apcserial.Temperature))
					if DEBUG :
						print(msg)
					send_message(msg)
					notice_count = 0
				sleep(SLEEP_SECONDS)
				notice_count += 1
			apcserial.serial_close()
		except Exception as e:
			print("Port %s APC not found or communication error : %s" % (PORT, e))
	
if __name__ == '__main__':
	main()
