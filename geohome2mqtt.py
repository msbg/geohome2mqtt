import requests, json
import paho.mqtt.client as mqtt
import time
from datetime import datetime
import os
import sys

BASE_URL='https://api.geotogether.com/'
LOGIN_URL='usersservice/v2/login'
DEVICEDETAILS_URL='api/userapi/v2/user/detail-systems?systemDetails=true'
LIVEDATA_URL = 'api/userapi/system/smets2-live-data/'
PERIODICDATA_URL = 'api/userapi/system/smets2-periodic-data/'
MQTT_ROOT = "geoHome"
MQTT_LIVE = "live"
MQTT_AGG = "totalConsumption"
CALORIFIC_VALUE = 39.5

USERNAME_KEY = "GEOHOME_USERNAME"
PASSWORD_KEY = "GEOHOME_PASSWORD"
MQTT_BROKER_ENV_VAR = "MQTT_BROKER"

class GeoHome:
      
    def __init__(self):
        
        log = "Start Intalising: " + str(datetime.now())
        
        try:
            if os.environ[USERNAME_KEY]:
                self.varUserName = os.environ[USERNAME_KEY]
                print("Setting usename to:", os.environ[USERNAME_KEY])
        except KeyError:
            print(USERNAME_KEY, 'environment variable is not set.')
            # Terminate from the script
            sys.exit(1)
        try:
            if os.environ[PASSWORD_KEY]:
                self.varPassword = os.environ[PASSWORD_KEY]
                print("Setting password to:", os.environ[PASSWORD_KEY])
        except KeyError:
            print(PASSWORD_KEY, 'environment variable is not set.')
            # Terminate from the script
            sys.exit(1)
        try:
            if os.environ[MQTT_BROKER_ENV_VAR]:
                self.varMqttBroker = os.environ[MQTT_BROKER_ENV_VAR]
                print("Setting Mqtt broker to:", os.environ[MQTT_BROKER_ENV_VAR])
        except KeyError:
            print(MQTT_BROKER_ENV_VAR, 'environment variable is not set.')
            # Terminate from the script
            sys.exit(1)
        
        self.headers = ""
        self.deviceId = ""
        self.authorise()
        self.getDevice()
        self.connectMqtt()
        log = log + os.linesep + "End Intalising: " + str(datetime.now())
        print(log)
  
    def connectMqtt(self):
        self.client = mqtt.Client("Geohome bridge")
        self.client.connect(self.varMqttBroker) 
    def authorise(self):
       data = { 'identity' : self.varUserName , 'password' : self.varPassword }
       r=requests.post(BASE_URL+LOGIN_URL, data=json.dumps(data), verify=False)
       authToken = json.loads(r.text)['accessToken']
       self.headers = {"Authorization": "Bearer " + authToken}
       return
   
    def getDevice(self):
        r=requests.get(BASE_URL+DEVICEDETAILS_URL, headers=self.headers)
        self.deviceId = json.loads(r.text)['systemRoles'][0]['systemId']
        print( 'Device Id:' + self.deviceId)
        return
  
    def run(self):
        periodic_count = 0
        while True:
            
            log ="Start Api Call: " + str(datetime.now())
            
            r=requests.get(BASE_URL+LIVEDATA_URL+ self.deviceId, headers=self.headers)
            #p=requests.get(BASE_URL+PERIODICDATA_URL+ self.deviceId, headers=self.headers)
            if r.status_code != 200:
                #Not successful. Assume Authentication Error
                log = log + os.linesep + "Request Status Error:" + str(r.status_code)
                #Reauthenticate. Need to add more error trapping here in case api goes down.
                self.authorise()
                self.getDevice()
            else:    
                log = log + os.linesep + json.dumps(r.text)
                power_dict =json.loads(r.text)['power']
                #Try and find the electricity usage
                try:
                    Electricity_usage=([x for x in power_dict if x['type'] == 'ELECTRICITY'][0]['watts'])
                    self.client.publish(MQTT_ROOT  + "/" + MQTT_LIVE + "/ElectricityWatts", Electricity_usage)
                    log = log + os.linesep + "Electricity_usage:"+str(Electricity_usage)
                except:
                    # Cant find Electricity in list. Add to log file but do nothing else
                    log = log + os.linesep + "No Electricity reading found"                    
    
                try:
                    Gas_usage=([x for x in power_dict if x['type'] == 'GAS_ENERGY'][0]['watts'])
                    self.client.publish(MQTT_ROOT  + "/" + MQTT_LIVE + "/GasWatts", Gas_usage)
                    log = log + os.linesep + "Gas Usage:" + str(Gas_usage)
                except:
                    # Cant find Gas in list. Add to log file but do nothing else
                    log = log + os.linesep + "No Gas reading found"
            if periodic_count == 0:
                p=requests.get(BASE_URL+PERIODICDATA_URL+ self.deviceId, headers=self.headers)
                if p.status_code == 200: 
                    log = log + os.linesep + json.dumps(p.text)
                    power_dict =json.loads(p.text)['totalConsumptionList']
                    #Try and find the electricity usage
                    try:
                        Electricity_usage=([x for x in power_dict if x['commodityType'] == 'ELECTRICITY'][0]['totalConsumption'])
                        self.client.publish(MQTT_ROOT  + "/" + MQTT_AGG + "/ElectricityWatts", Electricity_usage)
                        log = log + os.linesep + "Agg Electricity_usage:"+str(Electricity_usage)
                    except:
                        # Cant find Electricity in list. Add to log file but do nothing else
                        log = log + os.linesep + "No Agg Electricity reading found"                    
        
                    try:
                        Gas_usage=([x for x in power_dict if x['commodityType'] == 'GAS_ENERGY'][0]['totalConsumption'])
                        self.client.publish(MQTT_ROOT  + "/" + MQTT_AGG + "/GasWatts", Gas_usage)
                        log = log + os.linesep + "Agg Gas Usage:" + str(Gas_usage)
                    except:
                        # Cant find Gas in list. Add to log file but do nothing else
                        log = log + os.linesep + "No Agg Gas reading found"
                    
            #reset the periodic count every 20 mins
            periodic_count = periodic_count + 1
            if periodic_count > 20*2:
                periodic_count = 0
            #Always wait 30 secs here, so if worst happens and API goes down is we try every 30 secs.    
            time.sleep(30)
            
            print(log)  
            
# ConvertToKWH converts m3 to kWh
def ConvertToKWH(m3 , calorificValue):
	return (((m3 / 1000) * calorificValue) * 1.02264) / 3.6

t1 = GeoHome()
t1.run()