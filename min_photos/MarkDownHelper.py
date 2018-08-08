#! /usr/bin/python
#-*- coding: utf-8 -*-

from qiniu import Auth, put_file, etag, urlsafe_base64_encode
import qiniu.config
from qiniu import BucketManager
import sys,time
import os
import msvcrt
import datetime
import subprocess



# you will get md_url in this file
result_file = "ss.txt"  

if os.path.exists(result_file):
    os.remove(result_file)
os.chdir(sys.path[0])


# you need get yours msg here
access_key = "bIx0cXfydkhbTdjMlqF9oxi3oECUoAkvslImeiI3"
secret_key =  "eqHV7TWOj9puTww7Uk6oUulR-qBm_2A8u-5fckml"
bucket_name =  "android"
bucket_url =  "pcte8rzh8.bkt.clouddn.com"
md_url_result = "md_url.txt"
tag = "photo"
img_suffix = ["jpg", "jpeg", "png", "bmp", "gif"]

def upload_img(bucket_name,file_name,file_path):
    # generate token
	#print "file_name is %s" %file_name
    token = q.upload_token(bucket_name, file_name, 3600)
    info = put_file(token, file_name, file_path)
    # delete local imgFile
    #os.remove(file_path)
    return

def get_img_url(bucket_url,file_name):
    # ?imageMogr2/thumbnail/!65p
    file_names = file_name
    img_url = 'http://%s/%s' % (bucket_url,file_names)
    # generate md_url
    md_url = "![%s](%s)\n" % (file_name, img_url)
    return md_url


def save_to_txt(bucket_url,file_name):
    url_before_save = get_img_url(bucket_url,file_name)
    # save to clipBoard
    addToClipBoard(url_before_save)
    # save md_url to txt
    with open(md_url_result, "a") as f:
        f.write(url_before_save)
    return

# save to clipboard
def addToClipBoard(text):
	command = 'echo ' + text.strip() + '| clip'
	os.system(command)

if __name__ == '__main__':
    q = Auth(access_key, secret_key)
    bucket = BucketManager(q)
    imgs = sys.argv[1:]
    for img in imgs:
    	# name for img with local time 
        up_filename = 'min_photo/' +os.path.split(img)[1]
        upload_img(bucket_name,up_filename,img)
        save_to_txt(bucket_url,up_filename)
