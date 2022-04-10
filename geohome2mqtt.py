import traceback
import requests, json
import paho.mqtt.client as mqtt
from str2bool import str2bool
import time
from datetime import datetime
import os
import sys

BASE_URL='https://api.geotogether.com/'
LOGIN_URL='usersservice/v2/login'
DEVICEDETAILS_URL='api/userapi/v2/user/detail-systems?systemDetails=true'
LIVEDATA_URL = 'api/userapi/system/smets2-live-data/'
PERIODICDATA_URL = 'api/userapi/system/smets2-periodic-data/'
MQTT_LIVE = "live"
MQTT_AGG = "totalConsumption"
MQTT_ACTIVE_TARIFF = "activeTariff"
AUTH_POLL = (60 * 60 * 11) #Re-request auth every 11 hours
LIVE_DATA_POLL = 30 #Re-request live data every 30 secs
PERIODIC_DATA_POLL = (30 * 60) #Re-request periodic data every 30 mins
CALORIFIC_VALUE = 39.5

USERNAME_ENV_VAR = "GEOHOME_USERNAME"
PASSWORD_ENV_VAR = "GEOHOME_PASSWORD"
MQTT_BROKER_ENV_VAR = "MQTT_BROKER"
MQTT_PORT_ENV_VAR = "MQTT_PORT"
MQTT_TOPIC_ENV_VAR = "MQTT_TOPIC"
HASS_DICOVERY_ENV_VAR = "HASS_DISCOVERY"
HASS_DICOVERY_PERSIST_ENV_VAR = "HASS_DISCOVERY_PERSIST"
GAS_CALORIFIC_VAL_ENV_VAR = "GAS_CALORIFIC_VAL"

class GeoHome:
      
    def __init__(self):
        
        log = "Start Intalising: " + str(datetime.now())
        
        try:
            if os.environ[USERNAME_ENV_VAR]:
                self.varUserName = os.environ[USERNAME_ENV_VAR]
                print("Setting usename to:", os.environ[USERNAME_ENV_VAR])
        except KeyError:
            print(USERNAME_ENV_VAR, 'environment variable is not set.')
            # Terminate from the script
            sys.exit(1)
        try:
            if os.environ[PASSWORD_ENV_VAR]:
                self.varPassword = os.environ[PASSWORD_ENV_VAR]
                print("Setting password from ", PASSWORD_ENV_VAR)
        except KeyError:
            print(PASSWORD_ENV_VAR, 'environment variable is not set.')
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
        try:
            if os.environ[MQTT_PORT_ENV_VAR]:
                self.varMqttPort = int(os.environ[MQTT_PORT_ENV_VAR])
                print("Setting Mqtt port to:",self.varMqttPort)
        except KeyError:
            print(MQTT_PORT_ENV_VAR, 'environment variable is not set - using default of 1883')
            self.varMqttPort = 1883
        try:
            if os.environ[MQTT_TOPIC_ENV_VAR]:
                self.varMqttTopic = os.environ[MQTT_TOPIC_ENV_VAR]
                print("Setting Mqtt topic to:", os.environ[MQTT_TOPIC_ENV_VAR])
        except KeyError:
            print(MQTT_TOPIC_ENV_VAR, 'environment variable is not set - using default of \'geohome2mqtt\'')
            self.varMqttTopic = "geohome2mqtt"
        try:
            if os.environ[HASS_DICOVERY_ENV_VAR]:
                self.varHassDiscovery = str2bool(os.environ[HASS_DICOVERY_ENV_VAR])
                print("Setting HASS Discovery to:", self.varHassDiscovery)
        except KeyError:
            self.varHassDiscovery = False
            print(HASS_DICOVERY_ENV_VAR, 'environment variable is not set - using default of:', self.varHassDiscovery)
        try:
            if os.environ[HASS_DICOVERY_PERSIST_ENV_VAR]:
                self.varHassDiscoveryRetain = str2bool(os.environ[HASS_DICOVERY_PERSIST_ENV_VAR])
                print("Setting HASS Discovery Persist to:", self.varHassDiscoveryRetain)
        except KeyError:
            self.varHassDiscoveryRetain = True
            print(HASS_DICOVERY_PERSIST_ENV_VAR, 'environment variable is not set - using default of:', self.varHassDiscovery)
        try:
            if os.environ[GAS_CALORIFIC_VAL_ENV_VAR]:
                self.gasCalorificValue = float(os.environ[GAS_CALORIFIC_VAL_ENV_VAR])
                print("Setting Gas calorific value to:", self.gasCalorificValue)
        except KeyError:
            self.gasCalorificValue = CALORIFIC_VALUE
            print(GAS_CALORIFIC_VAL_ENV_VAR, 'environment variable is not set - using default of:', self.gasCalorificValue)
        
        
        self.headers = ""
        self.deviceId = ""
        self.discoverySent = False # We send the discovery info at least once, on startup, and every period poll if not persisted at the MQTT level
        self.connectMqtt()
        log = log + os.linesep + "End Intalising: " + str(datetime.now())
        print(log)
  
    def connectMqtt(self):
        self.client = mqtt.Client("Geohome bridge")
        self.client.connect(self.varMqttBroker, self.varMqttPort) 
    def authorise(self):
       data = { 'identity' : self.varUserName , 'password' : self.varPassword }
       r=requests.post(BASE_URL+LOGIN_URL, data=json.dumps(data), verify=False)
       authToken = json.loads(r.text)['accessToken']
       self.headers = {"Authorization": "Bearer " + authToken}
       return
   
    def getDevice(self):
        r=requests.get(BASE_URL+DEVICEDETAILS_URL, headers=self.headers)
        print(json.dumps(r.text))
        self.deviceId = json.loads(r.text)['systemRoles'][0]['systemId']
        self.deviceName = json.loads(r.text)['systemDetails'][0]['devices'][0]['deviceType']
        print( 'Device Id:' + self.deviceId)
        print( 'Device Name:' + self.deviceName)
        return

    def liveDataRequest(self):
        log = os.linesep
        r=requests.get(BASE_URL+LIVEDATA_URL+ self.deviceId, headers=self.headers)
        if r.status_code != 200:    
            log = log + os.linesep + "Live data Request Status Error:" + str(r.status_code) + ":" + r.reason
        else:    
            log = log + os.linesep + json.dumps(r.text)
            power_dict =json.loads(r.text)['power']
            #Try and find the electricity usage
            try:
                Electricity_usage=([x for x in power_dict if x['type'] == 'ELECTRICITY'][0]['watts'])
                self.client.publish(self.varMqttTopic  + "/" + self.deviceId +"/" + MQTT_LIVE + "/Electricity", Electricity_usage)
                log = log + os.linesep + "Electricity_usage:"+str(Electricity_usage)
            except:
                # Cant find Electricity in list. Add to log file but do nothing else
                log = log + os.linesep + "No Electricity reading found"                    

            try:
                Gas_usage=([x for x in power_dict if x['type'] == 'GAS_ENERGY'][0]['watts'])
                self.client.publish(self.varMqttTopic  + "/" + self.deviceId + "/" + MQTT_LIVE + "/Gas", Gas_usage)
                log = log + os.linesep + "Gas Usage:" + str(Gas_usage)
            except:
                # Cant find Gas in list. Add to log file but do nothing else
                log = log + os.linesep + "No Gas reading found"
        print(log)  
    
    def periodicDataRequest(self):
        log = os.linesep
        p=requests.get(BASE_URL+PERIODICDATA_URL+ self.deviceId, headers=self.headers)
        if p.status_code != 200:    
            log = log + os.linesep + "Periodic Request Status Error:" + str(p.status_code) + ":" + p.reason
        else:    
            log = log + os.linesep + json.dumps(p.text)
            power_dict =json.loads(p.text)['totalConsumptionList']
            tariff_dict =json.loads(p.text)['activeTariffList']
            #Try and find the electricity usage
            try:
                electricityUsageKWh=([x for x in power_dict if x['commodityType'] == 'ELECTRICITY'][0]['totalConsumption'])
                self.client.publish(self.varMqttTopic  + "/" + self.deviceId + "/" + MQTT_AGG + "/Electricity", electricityUsageKWh)
                electricityTariff=([x for x in tariff_dict if x['commodityType'] == 'ELECTRICITY'][0]['activeTariffPrice'])
                #I /think/ this is in pence per kWh, but need some data to verify - we're publishing in GBP/kWh so *100
                self.client.publish(self.varMqttTopic  + "/" + self.deviceId + "/" + MQTT_ACTIVE_TARIFF + "/Electricity", str(electricityTariff/100))
                log = log + os.linesep + "Agg Electricity Usage:"+str(electricityUsageKWh)
            except:
                # Cant find Electricity in list. Add to log file but do nothing else
                log = log + os.linesep + "No Agg Electricity reading found"                    

            try:
                gasUsageM3=([x for x in power_dict if x['commodityType'] == 'GAS_ENERGY'][0]['totalConsumption'])
                gasUsageKWh = self.ConvertToKWH(gasUsageM3)
                self.client.publish(self.varMqttTopic  + "/" + self.deviceId + "/" + MQTT_AGG + "/Gas", str(gasUsageKWh))
                gasTariff=([x for x in tariff_dict if x['commodityType'] == 'GAS_ENERGY'][0]['activeTariffPrice'])
                #I /think/ this is in pence per kWh, but need some data to verify - we're publishing in GBP/kWh so *100
                self.client.publish(self.varMqttTopic  + "/" + self.deviceId + "/" + MQTT_ACTIVE_TARIFF + "/Gas", str(gasTariff/100))
                log = log + os.linesep + "Agg Gas Usage:" + str(gasUsageKWh)
            except:
                traceback.print_exc()
                # Cant find Gas in list. Add to log file but do nothing else
                log = log + os.linesep + "No Agg Gas reading found"
        print(log) 

    # ConvertToKWH converts m3 to kWh
    def ConvertToKWH(self, m3):
        print("converting.." + str(m3))
        converted = (((m3 / 1000) * self.gasCalorificValue) * 1.02264) / 3.6
        print("converted.." + str(converted))
        return converted    
    def sendHassDiscovery(self):
        if self.discoverySent==False or self.varHassDiscoveryRetain==False:
            self.getDiscoveryMessage(MQTT_LIVE, "Gas", "W", "mdi:fire", "power", "measurement")
            self.getDiscoveryMessage(MQTT_LIVE, "Electricity", "W", "mdi:lightning-bolt", "power", "measurement")
            self.getDiscoveryMessage(MQTT_AGG, "Gas", "kWh", "mdi:fire", "energy", "total")
            self.getDiscoveryMessage(MQTT_AGG, "Electricity", "kWh", "mdi:lightning-bolt", "energy", "total")
            self.getDiscoveryMessage(MQTT_ACTIVE_TARIFF, "Gas", "GBP/kWh", "mdi:currency-gbp", "monetary", "measurement")
            self.getDiscoveryMessage(MQTT_ACTIVE_TARIFF, "Electricity", "GBP/kWh", "mdi:currency-gbp", "monetary", "measurement")
            self.discoverySent = True
    def getDiscoveryMessage(self, type, source, unit_of_measurement, icon, device_class, state_class):
        discovery_payload = {
               # "availability_topic": self._get_topic(
               #     key, description.platform, "availability"
               # ),
                "device": {
                    "identifiers": [self.deviceId],
                    "manufacturer": self.deviceName,
                    "model": self.deviceName,
                    "name": self.deviceName,
                    "sw_version": self.deviceName,
                },
                "name":f"geoHome_{type}_{source}",
                "device_class": device_class,
              #  "qos": 1,
                "unit_of_measurement": unit_of_measurement,
                "icon": icon,
                "state_topic": f"{self.varMqttTopic}/{self.deviceId}/{type}/{source}",
                "unique_id": f"{self.deviceId}_{type}_{source}_Id",
                "state_class": state_class
            }
        self.client.publish(f"homeassistant/sensor/{self.deviceId}/{type}{source}/config", json.dumps(discovery_payload).encode("utf-8"), retain=self.varHassDiscoveryRetain)

    def run(self):
        last_periodic_request = 0 
        last_auth_request = 0
        while True:
            
            print("Start Api Call: " + str(datetime.now()))
            #Re-auth every AUTH_POLL secs
            if time.time() > last_auth_request + AUTH_POLL:
                self.authorise()
                self.getDevice()
                last_auth_request = time.time()
            
            #Request periodic data every PERIODIC_DATA_POLL secs
            if time.time() > last_periodic_request + PERIODIC_DATA_POLL:
                self.sendHassDiscovery()
                self.periodicDataRequest()
                last_periodic_request = time.time()   
            
            #Always request the live data
            self.liveDataRequest()   
            print("Sleeping for:" + str(LIVE_DATA_POLL)) 
            time.sleep(LIVE_DATA_POLL)

            

t1 = GeoHome()
t1.run()