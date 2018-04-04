#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from pymongo import MongoClient
from tweepy.streaming import StreamListener
from tweepy import OAuthHandler
from tweepy import Stream
from datetime import datetime
import os
#import json
#from auth import TwitterAuth
import time
import sys

import csv

try:
    import smtplib
    from email.mime.text import MIMEText
except:
    sys.stderr.write("Error loading smtplib. Will not be able to send emails...\n")

# Output directory to hold json files (one per day) with tweets
# Within the output directory, the script loads a file named FILTER with the terms to be tracked (one per line)

outputDir = "."
consumer_key=''
consumer_secret=''

# After the step above, you will be redirected to your app's page.
# Create an access token under the the "Your access token" section
access_token='-'
access_token_secret=''

## End of Settings###

class FileDumperListener(StreamListener):
    
    def __init__(self,filepath):
        super(FileDumperListener,self).__init__(self)
        client = MongoClient('mongodb://localhost:27017')
        #client = MongoClient('0.0.0.0', 27017)
        self.db = client.twitter
        #self.basePath=filepath
        #os.system("mkdir -p %s"%(filepath))
        
        d=datetime.today()
        self.filename = "%i-%02d-%02d"%(d.year,d.month,d.day)
        self.collection = self.db[self.filename]	
        
        self.tweetCount=0
        self.errorCount=0
        self.limitCount=0
        self.last=datetime.now()
        
    #This function gets called every time a new tweet is received on the stream
    def on_data(self, data):
        #data = ast.literal_eval(data)
        #print data
        #print '*'*20
        s={'data':data}
        self.collection.insert_one(s)
        self.tweetCount+=1
        
        #Status method prints out vitals every five minutes and also rotates the log if needed
        self.status()
        return True
    
    def close(self):
        try:
            self.fh.close()
        except:
            #Log/email
            pass
	
    #Rotate the log file if needed.
    #Warning: Check for log rotation only occurs when a tweet is received and not more than once every five minutes.
    #		  This means the log file could have tweets from a neighboring period (especially for sparse streams)
    def rotateFiles(self):
        d=datetime.today()
        filenow = "%i-%02d-%02d"%(d.year,d.month,d.day)
        if (self.filename!=filenow):	
            print("%s - Rotating log file. Old: %s New: %s"%(datetime.now(),self.filename,filenow))
            
            self.filename=filenow
            self.collection = self.db[self.filename]	

    def on_error(self, statusCode):	
        print("%s - ERROR with status code %s"%(datetime.now(),statusCode))
        self.errorCount+=1
	
    def on_timeout(self):	
        raise TimeoutException()
	
    def on_limit(self, track):
        print("%s - LIMIT message recieved %s"%(datetime.now(),track))
        self.limitCount+=1
        
    def status(self):
        now=datetime.now()
        if (now-self.last).total_seconds()>600:
            print("%s - %i tweets, %i limits, %i errors in previous ten minutes."%(now,self.tweetCount,self.limitCount,self.errorCount))
            self.tweetCount=0
            self.limitCount=0
            self.errorCount=0
            self.last=now
            self.rotateFiles()#Check if file rotation is needed
            

class TimeoutException(Exception):
    pass

if __name__ == '__main__':
    while True:
        try:
            #Create the listener
            listener = FileDumperListener(outputDir)
            auth = OAuthHandler(consumer_key, consumer_secret)
            auth.set_access_token(access_token, access_token_secret)
            
            #fhTerms = open(outputDir+"/FILTER","r")
            #terms=[]
            #for line in fhTerms:
            #	terms.append(line.strip())
            print("%s - Starting stream to track %s"%(datetime.now(),"HSBC"))
            
            #Connect to the Twitter stream
            stream = Stream(auth, listener)
            keywords = ["viaje, viaje gratis, decimo viaje, descuento, beneficio"]
            #stream.filter(locations=[-0.530, 51.322, 0.231, 51.707])#Tweets from London
            stream.filter(track=keywords,languages=["es"])

        except KeyboardInterrupt:
            #User pressed ctrl+c or cmd+c -- get ready to exit the program
            print("%s - KeyboardInterrupt caught. Closing stream and exiting."%datetime.now())
            listener.close()
            stream.disconnect()
            break
        except TimeoutException:
            #Timeout error, network problems? reconnect.
            print("%s - Timeout exception caught. Closing stream and reopening."%datetime.now())
            try:
                listener.close()
                stream.disconnect()
            except:
                pass
            continue
        except Exception as e:
            #Anything else
            try:
                info = str(e)
                sys.stderr.write("%s - Unexpected exception. %s\n"%(datetime.now(),info))
                msg = MIMEText("Unexpected error in Twitter collector. Check server. %s"%info);
                msg['Subject'] = "Unexpected error in Twitter collector"
                msg['From'] = "youremail@example.com"
                msg['To'] = email
                s = smtplib.SMTP("smtp.example.com") #Update this to your SMTP server
                s.sendmail("youremail@example.com", email, msg.as_string())
                s.quit()
            except:
                pass
            time.sleep(1800)#Sleep thirty minutes and resume
			
