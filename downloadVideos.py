# coding=utf-8
from selenium import webdriver
import requests
from urllib.parse import unquote,urlparse,urljoin
import os
import re
from lxml import etree
import json
from downloadUtils import down_video_hls,down_video_mp4list,down_m3u8,down_video_mp4
import time

headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.81 Safari/537.36"}

def url_unquote(url):
    if url.count("%") > 5 or "%3" in url:
        url = unquote(url)
    return url

def switch_dir(fun):
    def wapper(*args, **kwargs):
        old_path = os.getcwd()
        path = kwargs.get('path') or './'
        os.chdir(path)
        try:
            return fun(*args, **kwargs)
        except:
            raise
        finally:
            os.chdir(old_path)
    return wapper

class SiguDownload:

    def __init__(self,video_name="",download_path=".",iterable_links=None,chromedriver=r"chromedriver"):
        self.video_name = video_name
        self.downloadPath = download_path
        self.download_links = iterable_links
        self.chromedriver = chromedriver

    def download_videos(self):
        self.download__init()
        try:
            downloadPath = os.path.join(self.downloadPath,self.video_name)
            if not os.path.exists(downloadPath):
                os.makedirs(downloadPath)
            downloaded_names = {os.path.splitext(d)[0] for d in os.listdir(downloadPath)}

            for href,name in self.download_links:
                if name in downloaded_names:
                    continue
                self.download_video_one_yuujx(href,name,path=downloadPath)
        finally:
            self.download_end()

    @switch_dir
    def download_video_one_yuujx(self,href,name,path):
        if self.driver.current_window_handle != self.driver_yuujx_handle:
            self.driver.switch_to.window(self.driver_yuujx_handle)
        response = self.session.get("https://api.bbbbbb.me/yuujx/?url={}".format(href), headers=headers)

        md5_match = re.search(r"eval\([^\(]+?\)", response.text)
        if not md5_match:
            return False
        js_str = self.hexs_to_ascii_str(md5_match.group()[6:-2].split(r"\x")[1:])
        if "hdMd5" not in js_str:
            return False
        md5 = re.search(r"val\([\"'](\w+?)[\"']\)", js_str).group(1)
        if not md5:
            return False
        md5 = self.driver.execute_script('return sign("' + md5 + '")')

        data = {"id": href,"type": "auto", "siteuser": "", "md5": md5, "hd": "", "lg": ""}
        response = self.session.post("https://api.bbbbbb.me/yuujx/api.php", data=data)
        return self.download_video_from_result_yuujx(response.json(),name)

    def download_video_from_result_yuujx(self,data,name):
        if str(data['msg']) != '200' :
            return False
        ext,url = data['ext'],urljoin("https://api.bbbbbb.me/yuujx/api.php",url_unquote(data["url"]))
        print(name,data,sep='\n')

        try:
            if ext == 'xml':
                response = self.session.get(url)
                urls = etree.XML(response.content).xpath("//video/file/text()")
                down_video_mp4list(self.session,urls[0:],name)
            elif ext in ['hls','hls_list']:
                down_video_hls(self.session,url,name)
            elif ext == 'mp4':
                down_video_mp4(self.session,url,name)
            elif ext in ['m3u8', 'm3u8_list','m3u8_list_youku','m3u8_list_iqiyi']:
                response = self.session.get(url)
                down_m3u8(self.session,response.text,name)
            elif ext == 'link':
                url = urljoin("https://api.bbbbbb.me/yuujx/?url=",url)
                result = urlparse(url)
                if result.hostname == "api.bbbbbb.me" and result.path == "/jiexi/":
                    return self.download_video_one_jiexi(url,name)
                else:
                    print("#" * 30 + data['ext'] + "-" + data["url"])
            else:
                print("#"*30+data['ext']+"-"+data["url"])
        except Exception as e:
            print(e)
            return False

        return True

    def download_video_one_jiexi(self,href,name):
        if self.driver.current_window_handle != self.driver_jiexi_handle:
            self.driver.switch_to.window(self.driver_jiexi_handle)
        #response = self.session.get("https://api.bbbbbb.me/jiexi/?url={}".format(href), headers=headers)
        response = self.session.get(href, headers=headers)

        md5_match = re.search(r"eval\([^\(]+?\)", response.text)
        if not md5_match:
            return False
        js_str = self.hexs_to_ascii_str(md5_match.group()[6:-2].split(r"\x")[1:])
        if "hdMd5" not in js_str:
            return False
        md5 = re.search(r"val\([\"'](\w+?)[\"']\)", js_str).group(1)
        if not md5:
            return False
        md5 = self.driver.execute_script('return desn("' + md5 + '")')

        js_str = re.search(r"api\.php[^\{]+?(\{[^\}]+?\})", response.text).group(1).replace(r"desn($('#hdMd5').val())", '""')
        data = json.loads(js_str)
        data["key"] = md5

        response = self.session.post("https://api.bbbbbb.me/jiexi/api.php", data=data)
        return self.download_video_from_result_jiexi(response.json(),name)

    def download_video_from_result_jiexi(self,data,name):
        if str(data['success']) != '1' :
            return False
        play,url = data['play'],urljoin("https://api.bbbbbb.me/jiexi/api.php",url_unquote(data["url"]))
        if url.count("%") > 5 or "%3" in url:
            url = unquote(url)
        print(name, data,sep='\n')

        try:
            if play == 'mp4':
                down_video_mp4(self.session,url,name)
            elif play == 'm3u8':
                response = self.session.get(url)
                down_m3u8(self.session,response.text,name)
            else:
                print("#"*30+play+"-"+data["url"])
        except Exception as e:
            print(e)
            return False

        return True

    def hexs_to_ascii_str(self,hexs):
        """#16进制转换ascii对应的str"""
        ascii_strs = [chr(int(hex, 16)) for hex in hexs]
        return "".join(ascii_strs)

    def download__init(self):
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        self.driver = webdriver.Chrome(self.chromedriver, options=chrome_options)
        self.driver.implicitly_wait(4)
        self.driver.get("file:///D:/pycharmWork/downVipVideo/html/siguStart.html")
        self.driver_yuujx_handle = self.driver.current_window_handle
        self.driver.execute_script("window.open('{}');".format("file:///D:/pycharmWork/downVipVideo/html/siguStart2.html"))
        for handle in self.driver.window_handles:
            if handle != self.driver_yuujx_handle:
                self.driver_jiexi_handle = handle
                break
        while self.driver.execute_script("return typeof sign == 'undefined' || typeof md5 == 'undefined'"):
            self.driver.get("file:///D:/pycharmWork/downVipVideo/html/siguStart.html")
            print("sleep 2 ...")
            time.sleep(2)
        self.driver.switch_to.window(self.driver_jiexi_handle)
        while self.driver.execute_script("return typeof desn == 'undefined'"):
            self.driver.get("file:///D:/pycharmWork/downVipVideo/html/siguStart.html2")
            print("sleep 2 ...")
            time.sleep(2)
        self.driver.switch_to.window(self.driver_yuujx_handle)
        self.session = requests.session()

    def download_end(self):
        self.session.close()
        self.driver.quit()

def get_youku_video_link():
    with open("video.html","r",encoding="utf-8") as fp:
        html = etree.HTML(fp.read())
    #links = html.xpath("//div[@id='bpmodule-main']//div[@class='sk-mod'][1]//ul[@class='mod-play-list play-list-num  tab-panel tab-1']/li/a")
    links = html.xpath("//ul[@class='mod-play-list play-list-num  tab-panel tab-1']/li/a")
    infos = list()
    nameset = set()
    for link in links:
        title = link.xpath("./@title")[0]
        href = link.xpath("./@href")[0]
        if title in nameset or href == "javascript:void(0);":
            continue
        nameset.add(title)
        infos.append((href,title))
    return infos

def get_iqiyi_video_link():
    with open("video_iqiyi.html","r",encoding="utf-8") as fp:
        html = etree.HTML(fp.read())
    links = html.xpath("//ul/li/a")
    infos = list()
    nameset = set()
    for link in links:
        title = link.xpath("./@title")[0]
        href = link.xpath("./@href")[0]
        if title in nameset or href == "javascript:void(0);":
            continue
        nameset.add(title)
        infos.append((href,title))
    return infos

if __name__ == "__main__":
    basepath = r"F:\vipvideos"
    name = "大宋提刑官"
    sigu = SiguDownload(name,basepath,get_iqiyi_video_link(),r"D:\apps\chromedriver_win32\chromedriver.exe")
    sigu.download_videos()
    ####11