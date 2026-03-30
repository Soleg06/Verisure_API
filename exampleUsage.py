from pprint import pprint

import arrow

from verisureGrafqlAPI import *

username = "firstname.lastname@something.com"
password = "**********"

vs = Verisure()
#vs.getMfaToken(username, password)
vs.login(False, username, password)
#vs.getAllInstallations()

print("getBatteryProcessStatus\n")
pprint(vs.getBatteryProcessStatus())

print("climate\n")
pprint(vs.getClimate())

print("doorwindow\n")
pprint(vs.getDoorWindow())

print("getPetType\n")
pprint(vs.getPetType())

print("getCommunication\n")
pprint(vs.getCommunication())

print("getCamera\n")
pprint(vs.getCamera())

print("armstate\n")
pprint(vs.getArmState())

print("bredband\n")
pprint(vs.getBroadbandStatus())

print("smartplug\n")
pprint(vs.read_smartplug_state())

print("usertracking\n")
pprint(vs.userTracking())

print("vaccationmode\n")
pprint(vs.getVacationMode())

#"eventCategories":["INTRUSION","FIRE","SOS","WATER","ANIMAL","TECHNICAL","WARNING","ARM","DISARM","LOCK","UNLOCK","PICTURE","CLIMATE","CAMERA_SETTINGS","DOORWINDOW_STATE_OPENED","DOORWINDOW_STATE_CLOSED"],

print("eventlogcategories\n")
categories = vs.getEventLogCategories()
pprint(categories)

print("History\n")
#pprint(vs.getEventLog("2022-03-01", "2022-03-04", ['TECHNICAL','FIRE','SOS','INTRUSION','CLIMATE','WARNING','POWERCONTROL','PICTURE','ARM','DISARM','CAMERA_SETTINGS','DOORWINDOW_STATE_OPENED','DOORWINDOW_STATE_CLOSED']))
pprint(vs.getEventLog(arrow.now().shift(days=-7), arrow.now(), categories))

print("getCommunications\n")
pprint(vs.getCommunication())

print("getInstallation\n")
pprint(vs.getInstallation())

print("getUsers\n")
pprint(vs.getUsers())

print("getvaccation and petsettings\n")
pprint(vs.getVacationModeAndPetSetting())

print("getCentralUnit")
pprint(vs.getCentralUnit())

#pprint(vs.getDevices())
#pprint(vs.isGuardianActivated())
#pprint(vs.getAllCardConfig())
#setArmStatusAway(code):
#setArmStatusHome(code):
#pprint(vs.getCapability())
#pprint(vs.chargeSms())
#disarmAlarm(self, code):
#doorLock(self, deviceLabel):
#doorUnlook(self, deviceLabel):
#pprint(vs.guardianSos())
#pprint(vs.permissions())
#pollArmState(self, transactionID, futurestate):
#pollLockState(self, transactionID, deviceLabel, futureState):
#pprint(vs.remainingSms())
#pprint(vs.smartButton())
#pprint(vs.smartLock())
#setSmartPlug(deviceLabel, state):
#getSmartplugState(devicelabel):
