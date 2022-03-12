import verisureGrafqlAPI
from pprint import pprint
import arrow

username = "firstname.lastname@something.com"
password = "**********"

vs = verisureGrafqlAPI.Verisure()
#vs.getMfaToken(username, password) this works but using it keeps logging out my iphone app....
vs.login(username, password)
#vs.getAllInstallations()

print("Climate\n")
pprint(vs.getClimate())

print("Doorwindow\n")
pprint(vs.getDoorWindow())

print("Armstate\n")
pprint(vs.getArmState())

print("Broadband\n")
pprint(vs.getBroadbandStatus())

print("Smartplug\n")
pprint(vs.read_smartplug_state())

print("Usertracking\n")
pprint(vs.userTracking())

print("Vaccationmode\n")
pprint(vs.getVacationMode())

print("Eventlogcategories\n")
categories = vs.getEventLogCategories()
pprint(categories)

print("Eventhistory\n")
#pprint(vs.getEventLog("2022-03-01", "2022-03-04", ['TECHNICAL','FIRE','SOS','INTRUSION','CLIMATE','WARNING','POWERCONTROL','PICTURE','ARM','DISARM','CAMERA_SETTINGS','DOORWINDOW_STATE_OPENED','DOORWINDOW_STATE_CLOSED']))
pprint(vs.getEventLog(arrow.now().shift(days=-7), arrow.now(), categories))

print("getCommunications\n")
pprint(vs.getCommunication())

print("getInstallation\n")
pprint(vs.getInstallation())

print("getUsers\n")
pprint(vs.getUsers())

print("getvacation and petsettings\n")
pprint(vs.getVacationModeAndPetSetting())

print("getCentralUnit")
pprint(vs.getCentralUnit())

pprint(vs.getDevices())
pprint(vs.isGuardianActivated())
pprint(vs.getAllCardConfig())
pprint(vs.getCapability())
pprint(vs.chargeSms())
pprint(vs.guardianSos())
pprint(vs.permissions())
pprint(vs.remainingSms())
pprint(vs.smartButton())
pprint(vs.smartLock())
setArmStatusAway(self, code):
setArmStatusHome(self, code):

#disarmAlarm(self, code):
#doorLock(self, deviceLabel):
#doorUnlook(self, deviceLabel):
#pollArmState(self, transactionID, futurestate):
#pollLockState(self, transactionID, deviceLabel, futureState):
#setSmartPlug(self, deviceLabel, state):
#getSmartplugState(self, devicelabel):

vs.logout()


