import asyncio
from pprint import pprint

import arrow

from verisureGrafqlAPI_async import *


async def main():
    
    username = "firstname.lastname@something.com"
    password = "**********"

    vs = Verisure()
    #await vs.getMfaToken(username, password)
    await vs.login(False, username, password)
    #await vs.getAllInstallations()

    #print("climate\n")
    #pprint(await vs.getClimate())

    #print("doorwindow\n")
    #pprint(await vs.getDoorWindow())

    #print("armstate\n")
    #pprint(await vs.getArmState())

    #print("bredband\n")
    #pprint(await vs.getBroadbandStatus())

    #print("smartplug\n")
    #pprint(await vs.read_smartplug_state())

    #print("usertracking\n")
    #pprint(await vs.userTracking())

    #print("vaccationmode\n")
    #pprint(await vs.getVacationMode())

    #['TECHNICAL',
    # 'FIRE',
    # 'SOS',
    # 'INTRUSION',
    # 'CLIMATE',
    # 'WARNING',
    # 'POWERCONTROL',
    # 'PICTURE',
    # 'ARM',
    # 'DISARM',
    # 'CAMERA_SETTINGS',
    # 'DOORWINDOW_STATE_OPENED',
    # 'DOORWINDOW_STATE_CLOSED']

    #"eventCategories":["INTRUSION","FIRE","SOS","WATER","ANIMAL","TECHNICAL","WARNING","ARM","DISARM","LOCK","UNLOCK","PICTURE","CLIMATE","CAMERA_SETTINGS","DOORWINDOW_STATE_OPENED","DOORWINDOW_STATE_CLOSED"],

    print("eventlogcategories\n")
    categories = await vs.getEventLogCategories()
    pprint(categories)

    print("History\n")
    #pprint(vs.getEventLog("2022-03-01", "2022-03-04", ['TECHNICAL','FIRE','SOS','INTRUSION','CLIMATE','WARNING','POWERCONTROL','PICTURE','ARM','DISARM','CAMERA_SETTINGS','DOORWINDOW_STATE_OPENED','DOORWINDOW_STATE_CLOSED']))
    pprint(await vs.getEventLog(arrow.now().shift(days=-7), arrow.now(), categories))

    print("getCommunications\n")
    pprint(await vs.getCommunication())


    print("getInstallation\n")
    pprint(await vs.getInstallation())


    print("getUsers\n")
    pprint(await vs.getUsers())

    print("getvaccation and petsettings\n")
    pprint(await vs.getVacationModeAndPetSetting())

    print("getCentralUnit")
    pprint(await vs.getCentralUnit())

    #pprint(await vs.getDevices())
    #pprint(await vs.isGuardianActivated())
    #pprint(await vs.getAllCardConfig())
    #setArmStatusAway(self, code):
    #setArmStatusHome(self, code):
    #pprint(await vs.getCapability())
    #pprint(await vs.chargeSms())
    #disarmAlarm(self, code):
    #doorLock(self, deviceLabel):
    #doorUnlook(self, deviceLabel):
    #pprint(await vs.guardianSos())
    #pprint(await vs.permissions())
    #pollArmState(self, transactionID, futurestate):
    #pollLockState(self, transactionID, deviceLabel, futureState):
    #pprint(await vs.remainingSms())
    #pprint(await vs.smartButton())
    #pprint(await vs.smartLock())
    #setSmartPlug(self, deviceLabel, state):
    #getSmartplugState(self, devicelabel):
    await vs.logout()

asyncio.run(main())