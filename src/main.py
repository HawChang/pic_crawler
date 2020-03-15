# -*- coding: utf-8 -*-

"""
File: main.py
Date: 2020/3/15 14:44
Author: zhanghao55
Email: zhanghao55@baidu.com
"""

import os  # 这个是用于文件目录操作
import shutil
import socket
import urllib
from multiprocessing import Pool, Lock

import requests
from bs4 import BeautifulSoup

# 设置超时时间为60s
socket.setdefaulttimeout(30)

opener = urllib.request.build_opener()
opener.addheaders = [('User-Agent',
                      'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1941.0 Safari/537.36')]
urllib.request.install_opener(opener)


def download_info(down, block, size):
    """
    回调函数：
    down：已经下载的数据块
    block：数据块的大小
    size：远程文件的大小
    """
    per = 100.0 * (down * block) / size
    if per > 100:
        per = 100
    print('%.2f%%' % per)


def download_pics(url, output_path, retry_max=5, retry_num=0):
    # try:
    if retry_num < retry_max:
        try:
            print("start download at %d try: %s" % (retry_num, output_path))
            urllib.request.urlretrieve(url, output_path + ".tmp")
            print("finish download: %s" % output_path)
            shutil.move(output_path + ".tmp", output_path)
        except socket.timeout:
            download_pics(url, output_path, retry_max, retry_num + 1)
    else:
        print("download fail: %s" % output_path)
    # except Exception as e:
    #    print("error at url: %s, output_path: %s" % (url, output_path))
    #    raise e


def get_with_retry(url, timeout=10, retry_max=5, retry_num=0):
    print("get url at %d try: %s" % (retry_num, url))
    if retry_num < retry_max:
        try:
            return requests.get(url, timeout=timeout)
        except requests.exceptions.RequestException as e:
            return get_with_retry(url, timeout, retry_num=retry_num + 1)
    else:
        print("get url：%s fail." % url)


def get_pics(url, output_dir, pool, res_list):
    html_text = get_with_retry(url)
    if html_text is None:
        return
    # request会自己猜测网页编码 有时候会识别错误 这里在get后 显示指定网页编码
    html_text.encoding = "utf-8"
    soup = BeautifulSoup(html_text.text, 'html.parser')
    img_list = soup.select("div > .details-content.text-justify > p > img")
    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)
    for index, img in enumerate(img_list):
        img_url = img.attrs["src"]
        output_path = output_dir + "/%d.jpg" % index
        if os.path.exists(output_path):
            print("already exists: %s" % output_path)
            continue
        res = pool.apply_async(download_pics, args=(img_url, output_path,))
        res_list.append(res)


def init(l):
    global lock
    lock = l


def main(output_dir):
    url_prefix = "https://www.*****.com/"
    page_num = 153
    lock = Lock()
    img_pool = Pool(100, initializer=init, initargs=(lock,))
    res_list = list()
    for page in range(14, page_num + 1):
        cur_url = url_prefix + "piclist.x?classid=3&page=%d" % page
        html_text = get_with_retry(cur_url)
        if html_text is None:
            return
        # request会自己猜测网页编码 有时候会识别错误 这里在get后 显示指定网页编码
        html_text.encoding = "utf-8"
        soup = BeautifulSoup(html_text.text, 'html.parser')
        url_list = soup.select('div[class="layout-box clearfix"] > ul')[-1].select("li > a")
        # 遍历直接子节点
        for cur_li in url_list:
            # print(cur_li)
            cur_url = url_prefix + cur_li.attrs["href"]
            title = urllib.request.unquotte(cur_li.attrs["title"]) \
                .replace(".", "_").replace(":", "_").replace("/", "_").replace("*", "_") \
                .replace("<", "_").replace(">", "_")
            print("title: %s, url: %s" % (title, cur_url))
            get_pics(cur_url, output_dir + title, img_pool, res_list)

    img_pool.close()
    img_pool.join()
    for res in res_list:
        res.get()
    print("download finish")


if __name__ == "__main__":
    main(output_dir="../output/")
