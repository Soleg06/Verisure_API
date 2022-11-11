#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import pickle
from pprint import pprint

import arrow
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

DEFAULT_TIMEOUT = 20  # seconds


class TimeoutHTTPAdapter(HTTPAdapter):

    def __init__(self, *args, **kwargs):
        self.timeout = DEFAULT_TIMEOUT
        if "timeout" in kwargs:
            self.timeout = kwargs["timeout"]
            del kwargs["timeout"]
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        timeout = kwargs.get("timeout")
        if timeout is None:
            kwargs["timeout"] = self.timeout
        return super().send(request, **kwargs)


class Verisure:

    def __init__(self):

        self.session = requests.Session()

        assert_status_hook = lambda response, * \
            args, **kwargs: response.raise_for_status()
        self.session.hooks["response"].append(assert_status_hook)

        retry_strategy = Retry(
            total=10,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "¨TRACE", "POST"])

        self.session.mount(
            "http://", TimeoutHTTPAdapter(max_retries=retry_strategy))
        self.session.mount(
            "https://", TimeoutHTTPAdapter(max_retries=retry_strategy))

        self.username = None
        self.giid = None
        self.applicationID = "Python"
        self.headers = {
            "Content-Type": "application/json",
            "Host": "m-api01.verisure.com",
            "Cache-Control": "no-cache",
            "APPLICATION_ID": self.applicationID
        }

    # def __del__(self):

       # self.logout()

    def login(self, mfa: bool, username, password, cookieFileName='~/.verisure_mfa_cookie'):

        urls = ["https://m-api01.verisure.com/auth/login",
                "https://m-api02.verisure.com/auth/login"]

        self.username = username
        if mfa:
            # with mfa get the trustxxx token from saved file
            try:
                with open(os.path.expanduser(cookieFileName), 'rb') as f:
                    self.session.cookies = pickle.load(f)
                    # session cookies set now
            except:
                print("No tokenfile found \n")

            for url in urls:
                response = self.session.post(
                    url, headers=self.headers, auth=(username, password))
                # pprint(response.text)
                if 'errors' not in response.json():
                    self.getAllInstallations()
        else:
            try:
                response = self.session.post(
                    urls[0], headers=self.headers, auth=(username, password))
                print("login ")
                print(urls[0])
                # pprint(response.json())
                # pprint(response.status_code)
                if 'errors' not in response.json():
                    self.getAllInstallations()
            except:
                try:
                    response = self.session.post(
                        urls[1], headers=self.headers, auth=(username, password))
                    print("login except ")
                    print(urls[1])
                    # pprint(response.json())
                    # pprint(response.status_code)
                    if 'errors' not in response.json():
                        self.getAllInstallations()
                except Exception as e:
                    print("error in _login except")
                    print(e)

    def getMfaToken(self, username, password, cookieFileName='~/.verisure_mfa_cookie'):

        self.username = username

        # Step 1: call auth/login with username and password and get a stepUpToken in reply valid 1200 seconds i.e. 20 minutes
        response = self.session.post(
            "https://m-api01.verisure.com/auth/login", headers=self.headers, auth=(username, password))

        # Step 2: call  auth/mfa and Verisure vill send you a SMS with a code valid for 300 seconds i.e 5 minutes
        response = self.session.post(
            "https://m-api01.verisure.com/auth/mfa", headers=self.headers)

        smsToken = input("Enter code sent by SMS: ")
        tok = dict()
        tok["token"] = smsToken

        # Step 3: call auth/mfa/validate with the SMS code and get an accesstoken in reply
        response = self.session.post(
            "https://m-api01.verisure.com/auth/mfa/validate", headers=self.headers, data=json.dumps(tok))
        # session.cookies contains stepUpCookie, vid, vs-access and vs-refresh

        # Step 4:  call auth/trust and get the trust token
        response = self.session.post(
            "https://m-api01.verisure.com/auth/trust", headers=self.headers)
        # session.cookies contains stepUpCookie, vid, vs-access, vs-refresh and vs-trustxxx

        # Step 5: save only trustxxx session.cookies to file
        self.session.cookies["vs-access"] = None
        self.session.cookies["vs-stepup"] = None
        self.session.cookies["vs-refresh"] = None
        self.session.cookies["vid"] = None
        with open(os.path.expanduser(cookieFileName), 'wb') as f:
            pickle.dump(self.session.cookies, f)

    def renewToken(self):

        urls = ['https://m-api01.verisure.com/auth/token',
                'https://m-api02.verisure.com/auth/token']

        try:
            response = self.session.post(urls[0], headers=self.headers)
        except:
            try:
                response = self.session.post(urls[1], headers=self.headers)

            except Exception as e:
                print("error in renewToken")
                print(e)

    def logout(self):

        urls = ['https://m-api01.verisure.com/auth/delete',
                'https://m-api02.verisure.com/auth/delete']

        try:
            response = self.session.delete(urls[0], headers=self.headers)
        except:
            try:
                response = self.session.delete(urls[1], headers=self.headers)

            except Exception as e:
                print("error in logout")
                print(e)

    def _doRequest(self, body):

        urls = ['https://m-api01.verisure.com/graphql',
                'https://m-api02.verisure.com/graphql']

        try:
            response = self.session.post(
                urls[0], headers=self.headers, data=json.dumps(list(body)))
            response.encoding = 'utf-8'
            # pprint(response.json())
            # pprint(response.status_code)
            if 'errors' in response.json():
                response2 = self.session.post(
                    urls[1], headers=self.headers, data=json.dumps(list(body)))
                response2.encoding = 'utf-8'
                # pprint(response2.json())
                # pprint(response2.status_code)
                if 'errors' in response2.json():
                    return {}
                else:
                    return response2.json()
            else:
                return response.json()

        except Exception as e:
            print("error in _doRequest")
            print(e)

        return {}

    def getAllInstallations(self):

        body = [{
            "operationName": "fetchAllInstallations",
            "variables": {
                "email": self.username},
            "query": "query fetchAllInstallations($email: String!){\n  account(email: $email) {\n    installations {\n      giid\n      alias\n      customerType\n      dealerId\n      subsidiary\n      pinCodeLength\n"
            "locale\n      address {\n        street\n        city\n        postalNumber\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = self._doRequest(body)

        for d in response["data"]["account"]["installations"]:
            self.giid = d["giid"]

        return response

    def getBatteryProcessStatus(self):

        body = [{
            "operationName": "batteryDevices",
            "variables": {
                "giid": self.giid},
            "query": "query batteryDevices($giid: String!) {\n  installation(giid: $giid) {\n    batteryDevices {\n      device {\n        area\n        deviceLabel\n        gui {\n          picture\n          label\n          __typename\n"
            "}\n        __typename\n      }\n      batteryCount\n      recommendedToChange\n      batteryTrend\n      estimatedRemainingBatteryLifetime\n      batteryType\n      batteryHealth\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = self._doRequest(body)

        out = dict()
        for d in response["data"]["installation"]["batteryDevices"]:
            name = d["device"]["area"] + "/" + d["device"]["gui"]["label"]
            out[name] = dict()
            out[name]["batteryHealth"] = d["batteryHealth"]
            out[name]["estimatedRemainingBatteryLifetime"] = d["estimatedRemainingBatteryLifetime"]
            out[name]["recommendedToChange"] = d["recommendedToChange"]

        return out

    def getClimate(self):

        body = [{
            "operationName": "Climate",
            "variables": {
                "giid": self.giid},
            "query": "query Climate($giid: String!) {\n  installation(giid: $giid) {\n    climates {\n      device {\n        deviceLabel\n        area\n        gui {\n          label\n          support\n          __typename\n"
            "}\n                 __typename\n      }\n      humidityEnabled\n      humidityTimestamp\n      humidityValue\n      temperatureTimestamp\n      temperatureValue\n      supportsThresholdSettings\n"
            "thresholds {\n        aboveMaxAlert\n                  belowMinAlert\n        sensorType\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = self._doRequest(body)

        out = dict()
        for d in response["data"]["installation"]["climates"]:
            name = d["device"]["area"] + "/" + d["device"]["gui"]["label"]
            out[name] = dict()
            out[name]["temperature"] = d["temperatureValue"]
            out[name]["timestamp"] = arrow.get(d["temperatureTimestamp"]).to(
                'Europe/Stockholm').format("YYYY-MM-DD HH:mm:ss")

        return out

    def userTracking(self):

        body = [{
            "operationName": "userTrackings",
            "variables": {
                "giid": self.giid},
            "query": "query userTrackings($giid: String!) {\n  installation(giid: $giid) {\n    userTrackings {\n      isCallingUser\n      webAccount\n      status\n      xbnContactId\n      currentLocationName\n"
            "deviceId\n      name\n      initials\n      currentLocationTimestamp\n      deviceName\n      currentLocationId\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = self._doRequest(body)

        out = dict()

        for d in response["data"]["installation"]["userTrackings"]:
            name = d["name"]
            out[name] = dict()

            if (d["currentLocationName"] != None):
                out[name]["currentLocationName"] = d["currentLocationName"]
            else:
                out[name]["currentLocationName"] = "None"

            if (d["currentLocationTimestamp"] != None):
                out[name]["timestamp"] = arrow.get(d["currentLocationTimestamp"]).to(
                    'Europe/Stockholm').format("YYYY-MM-DD HH:mm:ss")
            else:
                out[name]["timestamp"] = arrow.get(
                    '1970-01-01 00:00:00').format("YYYY-MM-DD HH:mm:ss")

        return out

    def getAllCardConfig(self):

        body = [{
            "operationName": "AllCardConfig",
            "variables": {
                "giid": self.giid},
            "query": "query AllCardConfig($giid: String!) {\n  installation(giid: $giid) {\n    allCardConfig {\n      cardName\n      selection\n      visible\n      items {\n        id\n        visible\n"
            "__typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = self._doRequest(body)
        return response

    def getVacationMode(self):

        body = [{
            "operationName": "VacationMode",
            "variables": {
                "giid": self.giid},
            "query": "query VacationMode($giid: String!) {\n  installation(giid: $giid) {\n    vacationMode {\n      isAllowed\n      turnOffPetImmunity\n      fromDate\n      toDate\n      temporaryContactName\n"
            "temporaryContactPhone\n      active\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = self._doRequest(body)
        out = dict()

        name = response["data"]["installation"]["vacationMode"]["__typename"]
        out[name] = dict()
        out[name]["active"] = response["data"]["installation"]["vacationMode"]["active"]

        if (response["data"]["installation"]["vacationMode"]["fromDate"] == None):
            out[name]["toDate"] = None
        else:
            arrow.get(response["data"]["installation"]["vacationMode"]["fromDate"]).to(
                'Europe/Stockholm').format("YYYY-MM-DD HH:mm:ss")

        if (response["data"]["installation"]["vacationMode"]["toDate"] == None):
            out[name]["toDate"] = None
        else:
            out[name]["toDate"] = arrow.get(response["data"]["installation"]["vacationMode"]["toDate"]).to(
                'Europe/Stockholm').format("YYYY-MM-DD HH:mm:ss")

        out[name]["contactName"] = response["data"]["installation"]["vacationMode"]["temporaryContactName"]
        out[name]["contactPhone"] = response["data"]["installation"]["vacationMode"]["temporaryContactPhone"]

        return out

    def getCommunication(self):

        body = [{
            "operationName": "communicationState",
            "variables": {
                "giid": self.giid},
            "query": "query communicationState($giid: String!) {\n  installation(giid: $giid) {\n    communicationState {\n      hardwareCarrierType\n      result\n      mediaType\n      device {\n        deviceLabel\n"
            "area\n        gui {\n          label\n          __typename\n        }\n        __typename\n      }\n      testDate\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = self._doRequest(body)

        out = dict()
        for d in response["data"]["installation"]["communicationState"]:
            name = d["device"]["area"]
            if out.get(name) == None:
                out[name] = list()

            part = dict()
            part["result"] = d["result"]
            part["hardwareCarrierType"] = d["hardwareCarrierType"]
            part["mediaType"] = d["mediaType"]
            part["timestamp"] = arrow.get(d["testDate"]).to(
                'Europe/Stockholm').format("YYYY-MM-DD HH:mm:ss")

            out[name].append(part)

        return out

    def getEventLogCategories(self):

        body = [{
            "operationName": "EventLogCategories",
            "variables": {
                "giid": self.giid},
            "query": "query EventLogCategories($giid: String!) {\n  installation(giid: $giid) {\n    notificationCategoryFilter\n    __typename\n  }\n}\n"}]

        response = self._doRequest(body)

        return response["data"]["installation"]["notificationCategoryFilter"]

    def getEventLog(self, fromDate, toDate, eventCategories):

        # "eventCategories":["INTRUSION","FIRE","SOS","WATER","ANIMAL","TECHNICAL","WARNING","ARM","DISARM","LOCK","UNLOCK","PICTURE","CLIMATE","CAMERA_SETTINGS","DOORWINDOW_STATE_OPENED","DOORWINDOW_STATE_CLOSED"],

        body = [{
            "operationName": "EventLog",
            "variables": {
                "hideNotifications": True,
                "offset": 0,
                "pagesize": 255,
                "eventCategories": eventCategories,
                "giid": self.giid,
                "eventContactIds": [],
                "fromDate":arrow.get(fromDate).format("YYYYMMDD"),
                "toDate":arrow.get(toDate).format("YYYYMMDD")},
            "query":"query EventLog($giid: String!, $offset: Int!, $pagesize: Int!, $eventCategories: [String], $fromDate: String, $toDate: String, $eventContactIds: [String]) {\n  installation(giid: $giid) {\n"
            "eventLog(offset: $offset, pagesize: $pagesize, eventCategories: $eventCategories, eventContactIds: $eventContactIds, fromDate: $fromDate, toDate: $toDate) {\n      moreDataAvailable\n"
            "pagedList {\n        device {\n          deviceLabel\n          area\n          gui {\n            label\n            __typename\n          }\n          __typename\n        }\n"
            "arloDevice {\n          name\n          __typename\n        }\n        gatewayArea\n        eventType\n        eventCategory\n        eventId\n        eventTime\n        userName\n"
            "armState\n        userType\n        climateValue\n        sensorType\n        eventCount\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = self._doRequest(body)

        out = dict()

        for d in response["data"]["installation"]["eventLog"]["pagedList"]:
            name = d["eventCategory"]
            if out.get(name) == None:
                out[name] = list()

            part = dict()
            part["device"] = d["device"]["area"]
            part["timestamp"] = arrow.get(d["eventTime"]).to(
                'Europe/Stockholm').format("YYYY-MM-DD HH:mm:ss")
            if (name in ["ARM", "DISARM"]):
                part["user"] = d["userName"]
                part["armState"] = d["armState"]

            out[name].append(part)

        return out

    def getInstallation(self):

        body = [{
            "operationName": "Installation",
            "variables": {
                "giid": self.giid},
            "query": "query Installation($giid: String!) {\n  installation(giid: $giid) {\n    alias\n    pinCodeLength\n    customerType\n    notificationCategoryFilter\n    userNotificationCategories\n"
            "doorWindowReportState\n    dealerId\n    isOperatorMonitorable\n    removeInstallationNotAllowed\n    installationNumber\n    editInstallationAddressNotAllowed\n    locale\n"
            "editGuardInformationAllowed\n    __typename\n  }\n}\n"}]

        response = self._doRequest(body)

        return response["data"]["installation"]

    def getUsers(self):

        body = [{
            "operationName": "Users",
            "variables": {
                "giid": self.giid},
            "query": "fragment Users on User {\n  profile\n  accessCodeChangeInProgress\n  hasDoorLockTag\n  pendingInviteProfile\n  relationWithInstallation\n  contactId\n  accessCodeSetTransactionId\n  userIndex\n  name\n"
            "hasTag\n  hasDoorLockPin\n  hasDigitalSignatureKey\n  email\n  mobilePhoneNumber\n  callOrder\n  tagColor\n  phoneNumber\n  webAccount\n  doorLockUser\n  alternativePhoneNumber\n  keyHolder\n"
            "hasCode\n  pendingInviteStatus\n  xbnContactId\n  userAccessTimeLimitation {\n    activeOnMonday\n    activeOnTuesday\n    activeOnWednesday\n    activeOnThursday\n    activeOnFriday\n"
            "activeOnSaturday\n    activeOnSunday\n    fromLocalDate\n    toLocalDate\n    toLocalTimeOfDay\n    fromLocalTimeOfDay\n    __typename\n  }\n  __typename\n}\n\nquery Users($giid: String!)"
            "{\n  users(giid: $giid) {\n    ...Users\n    notificationTypes\n    notificationSettings {\n      contactFilter {\n        contactName\n        filterContactId\n        __typename\n      }\n"
            "notificationCategory\n      notificationType\n      optionFilter\n      __typename\n    }\n    keyfob {\n      device {\n        deviceLabel\n        area\n        __typename\n      }\n"
            "__typename\n    }\n    __typename\n  }\n}\n"}]

        response = self._doRequest(body)

        return response["data"]["users"]

    def getVacationModeAndPetSetting(self):

        body = [{
            "operationName": "VacationModeAndPetSettings",
            "variables": {
                "giid": self.giid},
            "query": "query VacationModeAndPetSettings($giid: String!) {\n  installation(giid: $giid) {\n    vacationMode {\n      isAllowed\n      turnOffPetImmunity\n      fromDate\n      toDate\n      temporaryContactName\n"
            "temporaryContactPhone\n      active\n      __typename\n    }\n    petSettings {\n      devices {\n        area\n        deviceLabel\n        petSettingsActive\n        __typename\n      }\n"
            "__typename\n    }\n    __typename\n  }\n}\n"}]

        response = self._doRequest(body)

        out = dict()
        for d in response["data"]["installation"]["petSettings"]["devices"]:
            name = d["area"]
            out[name] = dict()
            out[name]["petSettingsActive"] = d["petSettingsActive"]

        name = response["data"]["installation"]["vacationMode"]["__typename"]
        out[name] = dict()
        out[name]["active"] = response["data"]["installation"]["vacationMode"]["active"]

        if (response["data"]["installation"]["vacationMode"]["fromDate"] == None):
            out[name]["toDate"] = None
        else:
            arrow.get(response["data"]["installation"]["vacationMode"]["fromDate"]).to(
                'Europe/Stockholm').format("YYYY-MM-DD HH:mm:ss")

        if (response["data"]["installation"]["vacationMode"]["toDate"] == None):
            out[name]["toDate"] = None
        else:
            out[name]["toDate"] = arrow.get(response["data"]["installation"]["vacationMode"]["toDate"]).to(
                'Europe/Stockholm').format("YYYY-MM-DD HH:mm:ss")

        out[name]["contactName"] = response["data"]["installation"]["vacationMode"]["temporaryContactName"]
        out[name]["contactPhone"] = response["data"]["installation"]["vacationMode"]["temporaryContactPhone"]
        out[name]["turnOffPetImmunity"] = response["data"]["installation"]["vacationMode"]["turnOffPetImmunity"]

        return out

    def getPetType(self):

        body = [{"operationName": "GetPetType",
                "variables": {
                    "giid": self.giid},
                 "query": "query GetPetType($giid: String!) {\n  installation(giid: $giid) {\n    pettingSettings {\n      petType\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = self._doRequest(body)

        return response["data"]["installation"]["pettingSettings"]["petType"]

    def getCentralUnit(self):

        body = [{
            "operationName": "centralUnits",
            "variables": {
                "giid": self.giid},
            "query": "query centralUnits($giid: String!) {\n  installation(giid: $giid) {\n    centralUnits {\n      macAddress {\n        macAddressEthernet\n        __typename\n      }\n      device {\n        deviceLabel\n"
            "area\n        gui {\n          label\n          support\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = self._doRequest(body)

        out = dict()
        for d in response["data"]["installation"]["centralUnits"]:
            name = d["device"]["area"]
            out[name] = dict()
            out[name]["label"] = d["device"]["gui"]["label"]
            out[name]["macAddressEthernet"] = d["macAddress"]["macAddressEthernet"]

        return out

    def getDevices(self):

        body = [{
            "operationName": "Devices",
            "variables": {
                "giid": self.giid},
            "query": "fragment DeviceFragment on Device {\n  deviceLabel\n  area\n  capability\n  gui {\n    support\n    picture\n    deviceGroup\n    sortOrder\n    label\n    __typename\n  }\n  monitoring {\n"
            "operatorMonitored\n    __typename\n  }\n  __typename\n}\n\nquery Devices($giid: String!) {\n  installation(giid: $giid) {\n    devices {\n      ...DeviceFragment\n      canChangeEntryExit\n"
            "entryExit\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = self._doRequest(body)
        out = dict()

        for d in response["data"]["installation"]["devices"]:
            name = d["area"]
            out[name] = d
            #out[name][""] = d["currentLocationName"]
            #out[name]["timestamp"] = arrow.get(d["currentLocationTimestamp"]).format("YYYY-MM-DD HH:mm")

        return out

    def setArmStatusAway(self, code):

        body = [{
            "operationName": "armAway",
            "variables": {
                "giid": self.giid,
                "code": code},
            "query": "mutation armAway($giid: String!, $code: String!) {\n  armStateArmAway(giid: $giid, code: $code)\n}\n"}]

        response = self._doRequest(body)
        return response

    def setArmStatusHome(self, code):

        body = [{
            "operationName": "armHome",
            "variables": {
                "giid": self.giid,
                "code": code},
            "query": "mutation armHome($giid: String!, $code: String!) {\n  armStateArmHome(giid: $giid, code: $code)\n}\n"}]

        response = self._doRequest(body)
        return response

    def getArmState(self):

        body = [{
            "operationName": "ArmState",
            "variables": {
                "giid": self.giid},
            "query": "query ArmState($giid: String!) {\n  installation(giid: $giid) {\n    armState {\n      type\n      statusType\n      date\n      name\n      changedVia\n      __typename\n    }\n"
            "__typename\n  }\n}\n"}]

        response = self._doRequest(body)

        out = dict()
        name = response["data"]["installation"]["armState"]["__typename"]
        out[name] = dict()
        out[name]["statusType"] = response["data"]["installation"]["armState"]["statusType"]
        out[name]["changedVia"] = response["data"]["installation"]["armState"]["changedVia"]
        out[name]["timestamp"] = arrow.get(response["data"]["installation"]["armState"]["date"]).to(
            'Europe/Stockholm').format("YYYY-MM-DD HH:mm:ss")

        return out

    def getBroadbandStatus(self):

        body = [{
            "operationName": "Broadband",
            "variables": {
                "giid": self.giid},
            "query": "query Broadband($giid: String!) {\n  installation(giid: $giid) {\n    broadband {\n      testDate\n      isBroadbandConnected\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = self._doRequest(body)

        out = dict()
        name = response["data"]["installation"]["broadband"]["__typename"]
        out[name] = dict()
        out[name]["connected"] = response["data"]["installation"]["broadband"]["isBroadbandConnected"]
        out[name]["timestamp"] = arrow.get(response["data"]["installation"]["broadband"]["testDate"]).to(
            'Europe/Stockholm').format("YYYY-MM-DD HH:mm:ss")

        return out

    def getCamera(self):

        body = [{"operationName":"Camera",
                 "variables": {
                     "giid": self.giid,
                     "all": True},
                     "query":"fragment CommonCameraFragment on Camera {\n  device {\n    deviceLabel\n    area\n    capability\n    gui {\n      label\n      support\n      __typename\n    }\n    __typename\n  "
                     "}\n  type\n  latestImageCapture\n  motionDetectorMode\n  imageCaptureAllowedByArmstate\n  accelerometerMode\n  supportedBlockSettingValues\n  imageCaptureAllowed\n  initiallyConfigured\n  "
                     "imageResolution\n  hasMotionSupport\n  totalUnseenImages\n  canTakePicture\n  takePictureProblems\n  canStream\n  streamProblems\n  videoRecordSettingAllowed\n  microphoneSettingAllowed\n  "
                     "supportsFullDuplexAudio\n  fullDuplexAudioProblems\n  cvr {\n    supported\n    recording\n    availablePlaylistDays\n    __typename\n  }\n  __typename\n}\n\nquery Camera($giid: String!, $all: Boolean!)"
                     "{\n  installation(giid: $giid) {\n    cameras(allCameras: $all) {\n      ...CommonCameraFragment\n      canChangeEntryExit\n      entryExit\n      __typename\n    }\n    __typename\n  }\n}\n"}]
       
        response = self._doRequest(body)

        return response["data"]["installation"]["cameras"]

    def getCapability(self):

        body = [{
            "operationName": "Capability",
            "variables": {
                "giid": self.giid},
            "query": "query Capability($giid: String!) {\n  installation(giid: $giid) {\n    capability {\n      current\n      gained {\n        capability\n        __typename\n      }\n      __typename\n"
            "}\n    __typename\n  }\n}\n"}]

        response = self._doRequest(body)
        return response

    def chargeSms(self):

        body = [{
            "operationName": "ChargeSms",
            "variables": {
                "giid": self.giid},
            "query": "query ChargeSms($giid: String!) {\n  installation(giid: $giid) {\n    chargeSms {\n      chargeSmartPlugOnOff\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = self._doRequest(body)
        return response

    def disarmAlarm(self, code):

        body = [{
            "operationName": "disarm",
            "variables": {
                "giid": self.giid,
                "code": code},
            "query": "mutation disarm($giid: String!, $code: String!) {\n  armStateDisarm(giid: $giid, code: $code)\n}\n"}]

        response = self._doRequest(body)
        return response

    def doorLock(self, deviceLabel):

        body = [{
            "operationName": "DoorLock",
            "variables": {
                "giid": self.giid,
                "deviceLabel": deviceLabel},
            "query": "mutation DoorLock($giid: String!, $deviceLabel: String!, $input: LockDoorInput!) {\n  DoorLock(giid: $giid, deviceLabel: $deviceLabel, input: $input)\n}\n"}]

        response = self._doRequest(body)
        return response

    def doorUnlook(self, deviceLabel):

        body = [{
            "operationName": "DoorUnlock",
            "variables": {
                "giid": self.giid,
                "deviceLabel": deviceLabel},
            "input": code,
            "query": "mutation DoorUnlock($giid: String!, $deviceLabel: String!, $input: LockDoorInput!) {\n  DoorUnlock(giid: $giid, deviceLabel: $deviceLabel, input: $input)\n}\n"}]

        response = self._doRequest(body)
        return response

    def getDoorWindow(self):

        body = [{
            "operationName": "DoorWindow",
            "variables": {
                "giid": self.giid},
            "query": "query DoorWindow($giid: String!) {\n  installation(giid: $giid) {\n    doorWindows {\n      device {\n        deviceLabel\n        __typename\n      }\n      type\n      area\n      state\n"
            "wired\n      reportTime\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = self._doRequest(body)

        out = dict()
        for d in response["data"]["installation"]["doorWindows"]:
            name = d["area"]
            out[name] = dict()
            out[name]["state"] = d["state"]
            out[name]["timestamp"] = arrow.get(d["reportTime"]).to(
                'Europe/Stockholm').format("YYYY-MM-DD HH:mm:ss")

        return out

    def guardianSos(self):

        body = [{
            "operationName": "GuardianSos",
            "variables": {},
            "query": "query GuardianSos {\n  guardianSos {\n    serverTime\n    sos {\n      fullName\n      phone\n      deviceId\n      deviceName\n      giid\n      type\n      username\n      expireDate\n"
            "warnBeforeExpireDate\n      contactId\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = self._doRequest(body)
        return response

    def isGuardianActivated(self):

        body = [{
            "operationName": "IsGuardianActivated",
            "variables": {
                "giid": self.giid,
                "featureName": "GUARDIAN"},
            "query": "query IsGuardianActivated($giid: String!, $featureName: String!) {\n  installation(giid: $giid) {\n    activatedFeature {\n      isFeatureActivated(featureName: $featureName)\n      __typename\n"
            "}\n    __typename\n  }\n}\n"}]

        response = self._doRequest(body)
        return response

    def permissions(self):

        body = [{
            "operationName": "Permissions",
            "variables": {
                "giid": self.giid,
                "email": self.username},
            "query": "query Permissions($giid: String!, $email: String!) {\n  permissions(giid: $giid, email: $email) {\n    accountPermissionsHash\n    name\n    __typename\n  }\n}\n"}]

        response = self._doRequest(body)
        return response

    def pollArmState(self, transactionID, futurestate):

        body = [{
            "operationName": "pollArmState",
            "variables": {
                "giid": self.giid,
                "transactionId": transactionId,
                "futureState": futureState},
            "query": "query pollArmState($giid: String!, $transactionId: String, $futureState: ArmStateStatusTypes!) {\n  installation(giid: $giid) {\n"
            "armStateChangePollResult(transactionId: $transactionId, futureState: $futureState) {\n      result\n      createTime\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = self._doRequest(body)
        return response

    def pollLockState(self, transactionID, deviceLabel, futureState):

        body = [{
            "operationName": "pollLockState",
            "variables": {
                "giid": self.giid,
                "transactionId": transactionId,
                "deviceLabel": deviceLabel,
                "futureState": futureState},
            "query": "query pollLockState($giid: String!, $transactionId: String, $deviceLabel: String!, $futureState: DoorLockState!) {\n  installation(giid: $giid) {\n"
            "doorLockStateChangePollResult(transactionId: $transactionId, deviceLabel: $deviceLabel, futureState: $futureState) {\n      result\n      createTime\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = self._doRequest(body)
        return response

    def remainingSms(self):

        body = [{
            "operationName": "RemainingSms",
            "variables": {
                "giid": self.giid},
            "query": "query RemainingSms($giid: String!) {\n  installation(giid: $giid) {\n    remainingSms\n    __typename\n  }\n}\n"}]

        response = self._doRequest(body)
        return response

    def smartButton(self):

        body = [{
            "operationName": "SmartButton",
            "variables": {
                "giid": self.giid},
            "query": "query SmartButton($giid: String!) {\n  installation(giid: $giid) {\n    smartButton {\n      entries {\n        smartButtonId\n        icon\n        label\n        color\n        active\n"
            "action {\n          actionType\n          expectedState\n          target {\n            ... on Installation {\n              alias\n              __typename\n            }\n"
            "... on Device {\n              deviceLabel\n              area\n              gui {\n                label\n                __typename\n              }\n              featureStatuses(type: \"SmartPlug\")"
            "{\n                device {\n                  deviceLabel\n                  __typename\n                }\n                ... on SmartPlug {\n                  icon\n                  isHazardous\n"
            "__typename\n                }\n                __typename\n              }\n              __typename\n            }\n            __typename\n          }\n          __typename\n        }\n"
            "__typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = self._doRequest(body)
        return response

    def smartLock(self):

        body = [{
            "operationName": "SmartLock",
            "variables": {
                "giid": self.giid},
            "query": "query SmartLock($giid: String!) {\n  installation(giid: $giid) {\n    smartLocks {\n      lockStatus\n      doorState\n      lockMethod\n      eventTime\n      doorLockType\n      secureMode\n"
            "device {\n        deviceLabel\n        area\n        __typename\n      }\n      user {\n        name\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = self._doRequest(body)
        return response

    def setSmartPlug(self, deviceLabel, state):

        body = [{
            "operationName": "UpdateState",
            "variables": {
                "giid": self.giid,
                "deviceLabel": deviceLabel,
                "state": state},
            "query": "mutation UpdateState($giid: String!, $deviceLabel: String!, $state: Boolean!) {\n  SmartPlugSetState(giid: $giid, input: [{deviceLabel: $deviceLabel, state: $state}])}"}]

        response = self._doRequest(body)
        return response

    def getSmartplugState(self, devicelabel):

        body = [{
            "operationName": "SmartPlug",
            "variables": {
                "giid": self.giid,
                "deviceLabel": deviceLabel},
            "query": "query SmartPlug($giid: String!, $deviceLabel: String!) {\n  installation(giid: $giid) {\n    smartplugs(filter: {deviceLabels: [$deviceLabel]}) {\n      device {\n        deviceLabel\n        area\n"
            "__typename\n      }\n      currentState\n      icon\n      isHazardous\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = self._doRequest(body)
        return response

    def read_smartplug_state(self):

        body = [{
            "operationName": "SmartPlug",
            "variables": {
                "giid": self.giid},
            "query": "query SmartPlug($giid: String!) {\n  installation(giid: $giid) {\n    smartplugs {\n      device {\n        deviceLabel\n        area\n        __typename\n      }\n      currentState\n      icon\n"
            "isHazardous\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = self._doRequest(body)
        out = dict()

        for d in response["data"]["installation"]["smartplugs"]:
            name = d["device"]["area"]
            out[name] = d["currentState"]

        return out
