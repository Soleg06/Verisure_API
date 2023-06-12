#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import os
import pickle
from pprint import pprint
import structlog

import aiohttp
import arrow
import ujson


class Verisure:

    log = structlog.get_logger(__name__)
    
    def __init__(self):
        self._username = None
        self._giid = None
        self.tokenExpires = arrow.now("Europe/Stockholm")
        self._applicationID = "Python"
        self._headers = {
            "Content-Type": "application/json",
            "Host": "m-api01.verisure.com",
            "Cache-Control": "no-cache",
            "APPLICATION_ID": self._applicationID
        }
        self._session = aiohttp.ClientSession()

    async def _doSession(self, method, url, headers, data=None, params=None, auth=None):
        try:
            async with self._session.request(method=method, url=url, headers=headers, data=data, params=params, auth=auth) as response:
                try:
                    return await response.json()
                except:
                    return await response.text()
                
        except aiohttp.ClientConnectorError as e:
            self.log.error("Exception in _doSession Failed to connect to host", error=e)
            pass
                            
        except Exception as e:
            self.log.error("Exception in _doSession", error=e)
            return None

    async def login(self, mfa: bool, username, password, cookieFileName='~/.verisure_mfa_cookie'):
        _urls = ["https://m-api01.verisure.com/auth/login",
                 "https://m-api02.verisure.com/auth/login"]

        self.auth = aiohttp.BasicAuth(username, password)
        self._username = username

        if mfa:
            # with mfa get the trustxxx token from saved file
            try:
                with open(os.path.expanduser(cookieFileName), 'rb') as f:
                    self._session.cookies = pickle.load(f)
                    # session cookies set now
            except:
                self.log.error("No tokenfile found")

            for url in _urls:
                out = await self._doSession(method="POST", url=url, headers=self._headers, auth=self.auth)
                if 'errors' not in out:
                    await self.getAllInstallations()
        else:
            try:
                out = await self._doSession(method="POST", url=_urls[0], headers=self._headers, auth=self.auth)
                if 'errors' not in out:
                    print("login ")
                    print(_urls[0])
                    self.tokenExpires = arrow.now("Europe/Stockholm").shift(seconds=out['accessTokenMaxAgeSeconds'])
                    await self.getAllInstallations()
            except:
                try:
                    out = await self._doSession(method="POST", url=_urls[1], headers=self._headers, auth=self.auth)
                    if 'errors' not in out:
                        print("login except ")
                        print(_urls[1])
                        self.tokenExpires = arrow.now("Europe/Stockholm").shift(seconds=out['accessTokenMaxAgeSeconds'])
                        await self.getAllInstallations()

                except Exception as e:
                    self.log.error("Exception in login", error=e)


    async def getMfaToken(self, username, password, cookieFileName='~/.verisure_mfa_cookie'):
        self._username = username
        self.auth = aiohttp.BasicAuth(username, password)

        # Step 1: call auth/login with username and password and get a stepUpToken in reply valid 1200 seconds i.e. 20 minutes
        await self._doSession(method="POST", url="https://m-api01.verisure.com/auth/login", headers=self._headers, auth=self.auth)

        # Step 2: call  auth/mfa and Verisure vill send you a SMS with a code valid for 300 seconds i.e 5 minutes
        await self._doSession(method="POST", url="https://m-api01.verisure.com/auth/mfa", headers=self._headers)

        smsToken = input("Enter code sent by SMS: ")
        tok = dict()
        tok["token"] = smsToken

        # Step 3: call auth/mfa/validate with the SMS code and get an accesstoken in reply
        await self._doSession(method="POST", url="https://m-api01.verisure.com/auth/mfa/validate", headers=self._headers, data=ujson.dumps(tok))

        # session.cookies contains stepUpCookie, vid, vs-access and vs-refresh

        # Step 4:  call auth/trust and get the trust token
        await self._doSession(method="POST", url="https://m-api01.verisure.com/auth/trust", headers=self._headers)

        # session.cookies contains stepUpCookie, vid, vs-access, vs-refresh and vs-trustxxx

        # Step 5: save only trustxxx session.cookies to file
        self._session.cookies["vs-access"] = None
        self._session.cookies["vs-stepup"] = None
        self._session.cookies["vs-refresh"] = None
        self._session.cookies["vid"] = None
        with open(os.path.expanduser(cookieFileName), 'wb') as f:
            pickle.dump(self._session.cookies, f)

    async def renewToken(self):
        _urls = ['https://m-api01.verisure.com/auth/token',
                 'https://m-api02.verisure.com/auth/token']

        try:
            result = await self._doSession(method="POST", url=_urls[0], headers=self._headers)
            self.tokenExpires = arrow.now("Europe/Stockholm").shift(seconds=result['accessTokenMaxAgeSeconds'])
        except:
            try:
                result = await self._doSession(method="POST", url=_urls[1], headers=self._headers)
                self.tokenExpires = arrow.now("Europe/Stockholm").shift(seconds=result['accessTokenMaxAgeSeconds'])

            except Exception as e:
                self.log.error("Exception in renewToken", error=e)


    async def _validateToken(self):
        now = arrow.now("Europe/Stockholm")
        if (self.tokenExpires - now).total_seconds() < 30:
            self.log.info("renewing token")
            await self.renewToken()

    async def logout(self):
        _urls = ['https://m-api01.verisure.com/auth/logout',
                 'https://m-api02.verisure.com/auth/logout']

        try:
            await self._doSession(method="DELETE", url=_urls[0], headers=self._headers)
            await self._session.close()
        except:
            try:
                await self._doSession(method="DELETE", url=_urls[1], headers=self._headers)
                await self._session.close()

            except Exception as e:
                self.log.error("Exception in logout", error=e)


    async def _doRequest(self, body):
        _urls = ['https://m-api01.verisure.com/graphql',
                 'https://m-api02.verisure.com/graphql']

        try:
            await self._validateToken()
            out = await self._doSession(method="POST", url=_urls[0], headers=self._headers, data=ujson.dumps(list(body)))
            if 'errors' in out:
                out2 = await self._doSession(method="POST", url=_urls[1], headers=self._headers, data=ujson.dumps(list(body)))
                if 'errors' in out2:
                    return {}
                else:
                    return out2
            else:
                return out

        except Exception as e:
            self.log.error("Exception in _doRequest", error=e)
            
        return {}

    async def getAllInstallations(self):
        _body = [{
            "operationName": "fetchAllInstallations",
            "variables": {
                "email": self._username},
            "query": "query fetchAllInstallations($email: String!){\n  account(email: $email) {\n    installations {\n      giid\n      alias\n      customerType\n      dealerId\n      subsidiary\n      pinCodeLength\n"
            "locale\n      address {\n        street\n        city\n        postalNumber\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = await self._doRequest(_body)

        for d in response["data"]["account"]["installations"]:
            self._giid = d["giid"]

        return response

    async def getBatteryProcessStatus(self):
        _body = [{
            "operationName": "batteryDevices",
            "variables": {
                "giid": self._giid},
            "query": "query batteryDevices($giid: String!) {\n  installation(giid: $giid) {\n    batteryDevices {\n      device {\n        area\n        deviceLabel\n        gui {\n          picture\n          label\n          __typename\n"
            "}\n        __typename\n      }\n      batteryCount\n      recommendedToChange\n      batteryTrend\n      estimatedRemainingBatteryLifetime\n      batteryType\n      batteryHealth\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = await self._doRequest(_body)

        out = dict()
        for d in response["data"]["installation"]["batteryDevices"]:
            name = d["device"]["area"] + "/" + d["device"]["gui"]["label"]
            out[name] = dict()
            out[name]["batteryHealth"] = d["batteryHealth"]
            out[name]["estimatedRemainingBatteryLifetime"] = d["estimatedRemainingBatteryLifetime"]
            out[name]["recommendedToChange"] = d["recommendedToChange"]

        return out

    async def getClimate(self):
        _body = [{
            "operationName": "Climate",
            "variables": {
                "giid": self._giid},
            "query": "query Climate($giid: String!) {\n  installation(giid: $giid) {\n    climates {\n      device {\n        deviceLabel\n        area\n        gui {\n          label\n          support\n          __typename\n"
            "}\n                 __typename\n      }\n      humidityEnabled\n      humidityTimestamp\n      humidityValue\n      temperatureTimestamp\n      temperatureValue\n      supportsThresholdSettings\n"
            "thresholds {\n        aboveMaxAlert\n                  belowMinAlert\n        sensorType\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = await self._doRequest(_body)

        out = dict()
        for d in response["data"]["installation"]["climates"]:
            name = d["device"]["area"] + "/" + d["device"]["gui"]["label"]
            out[name] = dict()
            out[name]["temperature"] = d["temperatureValue"]
            out[name]["timestamp"] = arrow.get(d["temperatureTimestamp"]).to('Europe/Stockholm').format("YYYY-MM-DD HH:mm:ss")

        return out

    async def userTracking(self):
        _body = [{
            "operationName": "userTrackings",
            "variables": {
                "giid": self._giid},
            "query": "query userTrackings($giid: String!) {\n  installation(giid: $giid) {\n    userTrackings {\n      isCallingUser\n      webAccount\n      status\n      xbnContactId\n      currentLocationName\n"
            "deviceId\n      name\n      initials\n      currentLocationTimestamp\n      deviceName\n      currentLocationId\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = await self._doRequest(_body)

        out = dict()

        for d in response["data"]["installation"]["userTrackings"]:
            name = d["name"]
            out[name] = dict()

            if (d["currentLocationName"] is not None):
                out[name]["currentLocationName"] = d["currentLocationName"]
            else:
                out[name]["currentLocationName"] = "None"

            if (d["currentLocationTimestamp"] is not None):
                out[name]["timestamp"] = arrow.get(d["currentLocationTimestamp"]).to('Europe/Stockholm').format("YYYY-MM-DD HH:mm:ss")
            else:
                out[name]["timestamp"] = arrow.get('1970-01-01 00:00:00').format("YYYY-MM-DD HH:mm:ss")

        return out

    async def getAllCardConfig(self):
        _body = [{
            "operationName": "AllCardConfig",
            "variables": {
                "giid": self._giid},
            "query": "query AllCardConfig($giid: String!) {\n  installation(giid: $giid) {\n    allCardConfig {\n      cardName\n      selection\n      visible\n      items {\n        id\n        visible\n"
            "__typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = await self._doRequest(_body)
        return response

    async def getVacationMode(self):
        _body = [{
            "operationName": "VacationMode",
            "variables": {
                "giid": self._giid},
            "query": "query VacationMode($giid: String!) {\n  installation(giid: $giid) {\n    vacationMode {\n      isAllowed\n      turnOffPetImmunity\n      fromDate\n      toDate\n      temporaryContactName\n"
            "temporaryContactPhone\n      active\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = await self._doRequest(_body)
        out = dict()

        name = response["data"]["installation"]["vacationMode"]["__typename"]
        out[name] = dict()
        out[name]["active"] = response["data"]["installation"]["vacationMode"]["active"]

        if (response["data"]["installation"]["vacationMode"]["fromDate"] == None):
            out[name]["fromDate"] = None
        else:
            arrow.get(response["data"]["installation"]["vacationMode"]["fromDate"]).to('Europe/Stockholm').format("YYYY-MM-DD HH:mm:ss")

        if (response["data"]["installation"]["vacationMode"]["toDate"] == None):
            out[name]["toDate"] = None
        else:
            out[name]["toDate"] = arrow.get(response["data"]["installation"]["vacationMode"]["toDate"]).to('Europe/Stockholm').format("YYYY-MM-DD HH:mm:ss")

        out[name]["contactName"] = response["data"]["installation"]["vacationMode"]["temporaryContactName"]
        out[name]["contactPhone"] = response["data"]["installation"]["vacationMode"]["temporaryContactPhone"]

        return out

    async def getCommunication(self):
        _body = [{
            "operationName": "communicationState",
            "variables": {
                "giid": self._giid},
            "query": "query communicationState($giid: String!) {\n  installation(giid: $giid) {\n    communicationState {\n      hardwareCarrierType\n      result\n      mediaType\n      device {\n        deviceLabel\n"
            "area\n        gui {\n          label\n          __typename\n        }\n        __typename\n      }\n      testDate\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = await self._doRequest(_body)

        out = dict()
        for d in response["data"]["installation"]["communicationState"]:
            name = d["device"]["area"]
            if out.get(name) == None:
                out[name] = list()

            part = dict()
            part["result"] = d["result"]
            part["hardwareCarrierType"] = d["hardwareCarrierType"]
            part["mediaType"] = d["mediaType"]
            part["timestamp"] = arrow.get(d["testDate"]).to('Europe/Stockholm').format("YYYY-MM-DD HH:mm:ss")

            out[name].append(part)

        return out

    async def getEventLogCategories(self):
        _body = [{
            "operationName": "EventLogCategories",
            "variables": {
                "giid": self._giid},
            "query": "query EventLogCategories($giid: String!) {\n  installation(giid: $giid) {\n    notificationCategoryFilter\n    __typename\n  }\n}\n"}]

        response = await self._doRequest(_body)

        return response["data"]["installation"]["notificationCategoryFilter"]

    async def getEventLog(self, fromDate, toDate, eventCategories):
        # "eventCategories":["INTRUSION","FIRE","SOS","WATER","ANIMAL","TECHNICAL","WARNING","ARM","DISARM","LOCK","UNLOCK","PICTURE","CLIMATE","CAMERA_SETTINGS","DOORWINDOW_STATE_OPENED","DOORWINDOW_STATE_CLOSED"],

        _body = [{
            "operationName": "EventLog",
            "variables": {
                "hideNotifications": True,
                "offset": 0,
                "pagesize": 255,
                "eventCategories": eventCategories,
                "giid": self._giid,
                "eventContactIds": [],
                "fromDate":arrow.get(fromDate).format("YYYYMMDD"),
                "toDate":arrow.get(toDate).format("YYYYMMDD")},
            "query":"query EventLog($giid: String!, $offset: Int!, $pagesize: Int!, $eventCategories: [String], $fromDate: String, $toDate: String, $eventContactIds: [String]) {\n  installation(giid: $giid) {\n"
            "eventLog(offset: $offset, pagesize: $pagesize, eventCategories: $eventCategories, eventContactIds: $eventContactIds, fromDate: $fromDate, toDate: $toDate) {\n      moreDataAvailable\n"
            "pagedList {\n        device {\n          deviceLabel\n          area\n          gui {\n            label\n            __typename\n          }\n          __typename\n        }\n"
            "arloDevice {\n          name\n          __typename\n        }\n        gatewayArea\n        eventType\n        eventCategory\n        eventId\n        eventTime\n        userName\n"
            "armState\n        userType\n        climateValue\n        sensorType\n        eventCount\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = await self._doRequest(_body)

        out = dict()

        for d in response["data"]["installation"]["eventLog"]["pagedList"]:
            name = d["eventCategory"]
            if out.get(name) == None:
                out[name] = list()

            part = dict()
            part["device"] = d["device"]["area"]
            part["timestamp"] = arrow.get(d["eventTime"]).to('Europe/Stockholm').format("YYYY-MM-DD HH:mm:ss")
            if (name in ["ARM", "DISARM"]):
                part["user"] = d["userName"]
                part["armState"] = d["armState"]

            out[name].append(part)

        return out

    async def getInstallation(self):
        _body = [{
            "operationName": "Installation",
            "variables": {
                "giid": self._giid},
            "query": "query Installation($giid: String!) {\n  installation(giid: $giid) {\n    alias\n    pinCodeLength\n    customerType\n    notificationCategoryFilter\n    userNotificationCategories\n"
            "doorWindowReportState\n    dealerId\n    isOperatorMonitorable\n    removeInstallationNotAllowed\n    installationNumber\n    editInstallationAddressNotAllowed\n    locale\n"
            "editGuardInformationAllowed\n    __typename\n  }\n}\n"}]

        response = await self._doRequest(_body)

        return response["data"]["installation"]

    async def getUsers(self):
        _body = [{
            "operationName": "Users",
            "variables": {
                "giid": self._giid},
            "query": "fragment Users on User {\n  profile\n  accessCodeChangeInProgress\n  hasDoorLockTag\n  pendingInviteProfile\n  relationWithInstallation\n  contactId\n  accessCodeSetTransactionId\n  userIndex\n  name\n"
            "hasTag\n  hasDoorLockPin\n  hasDigitalSignatureKey\n  email\n  mobilePhoneNumber\n  callOrder\n  tagColor\n  phoneNumber\n  webAccount\n  doorLockUser\n  alternativePhoneNumber\n  keyHolder\n"
            "hasCode\n  pendingInviteStatus\n  xbnContactId\n  userAccessTimeLimitation {\n    activeOnMonday\n    activeOnTuesday\n    activeOnWednesday\n    activeOnThursday\n    activeOnFriday\n"
            "activeOnSaturday\n    activeOnSunday\n    fromLocalDate\n    toLocalDate\n    toLocalTimeOfDay\n    fromLocalTimeOfDay\n    __typename\n  }\n  __typename\n}\n\nquery Users($giid: String!)"
            "{\n  users(giid: $giid) {\n    ...Users\n    notificationTypes\n    notificationSettings {\n      contactFilter {\n        contactName\n        filterContactId\n        __typename\n      }\n"
            "notificationCategory\n      notificationType\n      optionFilter\n      __typename\n    }\n    keyfob {\n      device {\n        deviceLabel\n        area\n        __typename\n      }\n"
            "__typename\n    }\n    __typename\n  }\n}\n"}]

        response = await self._doRequest(_body)

        return response["data"]["users"]

    async def getVacationModeAndPetSetting(self):
        _body = [{
            "operationName": "VacationModeAndPetSettings",
            "variables": {
                "giid": self._giid},
            "query": "query VacationModeAndPetSettings($giid: String!) {\n  installation(giid: $giid) {\n    vacationMode {\n      isAllowed\n      turnOffPetImmunity\n      fromDate\n      toDate\n      temporaryContactName\n"
            "temporaryContactPhone\n      active\n      __typename\n    }\n    petSettings {\n      devices {\n        area\n        deviceLabel\n        petSettingsActive\n        __typename\n      }\n"
            "__typename\n    }\n    __typename\n  }\n}\n"}]

        response = await self._doRequest(_body)

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
            arrow.get(response["data"]["installation"]["vacationMode"]["fromDate"]).to('Europe/Stockholm').format("YYYY-MM-DD HH:mm:ss")

        if (response["data"]["installation"]["vacationMode"]["toDate"] == None):
            out[name]["toDate"] = None
        else:
            out[name]["toDate"] = arrow.get(response["data"]["installation"]["vacationMode"]["toDate"]).to('Europe/Stockholm').format("YYYY-MM-DD HH:mm:ss")

        out[name]["contactName"] = response["data"]["installation"]["vacationMode"]["temporaryContactName"]
        out[name]["contactPhone"] = response["data"]["installation"]["vacationMode"]["temporaryContactPhone"]
        out[name]["turnOffPetImmunity"] = response["data"]["installation"]["vacationMode"]["turnOffPetImmunity"]

        return out

    async def getPetType(self):
        _body = [{"operationName": "GetPetType",
                  "variables": {
                      "giid": self._giid},
                 "query": "query GetPetType($giid: String!) {\n  installation(giid: $giid) {\n    pettingSettings {\n      petType\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = await self._doRequest(_body)

        return response["data"]["installation"]["pettingSettings"]["petType"]

    async def getCentralUnit(self):
        _body = [{
            "operationName": "centralUnits",
            "variables": {
                "giid": self._giid},
            "query": "query centralUnits($giid: String!) {\n  installation(giid: $giid) {\n    centralUnits {\n      macAddress {\n        macAddressEthernet\n        __typename\n      }\n      device {\n        deviceLabel\n"
            "area\n        gui {\n          label\n          support\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = await self._doRequest(_body)

        out = dict()
        for d in response["data"]["installation"]["centralUnits"]:
            name = d["device"]["area"]
            out[name] = dict()
            out[name]["label"] = d["device"]["gui"]["label"]
            out[name]["macAddressEthernet"] = d["macAddress"]["macAddressEthernet"]

        return out

    async def getDevices(self):
        _body = [{"operationName": "Devices",
                  "variables": {
                      "giid": self._giid},
                 "query": "fragment DeviceFragment on Device {\n  deviceLabel\n  area\n  capability\n  gui {\n    support\n    picture\n    deviceGroup\n    sortOrder\n    label\n    __typename\n  }\n  monitoring {\n"
                  "operatorMonitored\n    __typename\n  }\n  __typename\n}\n\nquery Devices($giid: String!) {\n  installation(giid: $giid) {\n    devices {\n      ...DeviceFragment\n      canChangeEntryExit\n"
                  "entryExit\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = await self._doRequest(_body)
        out = list()

        for d in response["data"]["installation"]["devices"]:
            label = d["gui"]["label"]
            namn = d["area"]
            out.append(f"{namn}/{label}")
            # out[label] = {"namn": d["area"], "label": d["gui"]["label"]}
            # out[name][""] = d["currentLocationName"]
            # out[name]["timestamp"] = arrow.get(d["currentLocationTimestamp"]).format("YYYY-MM-DD HH:mm")

        return out

    async def setArmStatusAway(self, code):
        _body = [{
            "operationName": "armAway",
            "variables": {
                "giid": self._giid,
                "code": code},
            "query": "mutation armAway($giid: String!, $code: String!) {\n  armStateArmAway(giid: $giid, code: $code)\n}\n"}]

        response = await self._doRequest(_body)
        return response

    async def setArmStatusHome(self, code):
        _body = [{
            "operationName": "armHome",
            "variables": {
                "giid": self._giid,
                "code": code},
            "query": "mutation armHome($giid: String!, $code: String!) {\n  armStateArmHome(giid: $giid, code: $code)\n}\n"}]

        response = await self._doRequest(_body)
        return response

    async def getArmState(self):
        _body = [{
            "operationName": "ArmState",
            "variables": {
                "giid": self._giid},
            "query": "query ArmState($giid: String!) {\n  installation(giid: $giid) {\n    armState {\n      type\n      statusType\n      date\n      name\n      changedVia\n      __typename\n    }\n"
            "__typename\n  }\n}\n"}]

        response = await self._doRequest(_body)

        out = dict()
        name = response["data"]["installation"]["armState"]["__typename"]
        out[name] = dict()
        out[name]["statusType"] = response["data"]["installation"]["armState"]["statusType"]
        out[name]["changedVia"] = response["data"]["installation"]["armState"]["changedVia"]
        out[name]["timestamp"] = arrow.get(response["data"]["installation"]["armState"]["date"]).to('Europe/Stockholm').format("YYYY-MM-DD HH:mm:ss")

        return out

    async def getBroadbandStatus(self):
        _body = [{
            "operationName": "Broadband",
            "variables": {
                "giid": self._giid},
            "query": "query Broadband($giid: String!) {\n  installation(giid: $giid) {\n    broadband {\n      testDate\n      isBroadbandConnected\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = await self._doRequest(_body)

        out = dict()
        name = response["data"]["installation"]["broadband"]["__typename"]
        out[name] = dict()
        out[name]["connected"] = response["data"]["installation"]["broadband"]["isBroadbandConnected"]
        out[name]["timestamp"] = arrow.get(response["data"]["installation"]["broadband"]["testDate"]).to('Europe/Stockholm').format("YYYY-MM-DD HH:mm:ss")

        return out

    async def getCamera(self):
        _body = [{"operationName": "Camera",
                 "variables": {
                     "giid": self._giid,
                     "all": True},
                  "query": "fragment CommonCameraFragment on Camera {\n  device {\n    deviceLabel\n    area\n    capability\n    gui {\n      label\n      support\n      __typename\n    }\n    __typename\n  "
                  "}\n  type\n  latestImageCapture\n  motionDetectorMode\n  imageCaptureAllowedByArmstate\n  accelerometerMode\n  supportedBlockSettingValues\n  imageCaptureAllowed\n  initiallyConfigured\n  "
                  "imageResolution\n  hasMotionSupport\n  totalUnseenImages\n  canTakePicture\n  takePictureProblems\n  canStream\n  streamProblems\n  videoRecordSettingAllowed\n  microphoneSettingAllowed\n  "
                  "supportsFullDuplexAudio\n  fullDuplexAudioProblems\n  cvr {\n    supported\n    recording\n    availablePlaylistDays\n    __typename\n  }\n  __typename\n}\n\nquery Camera($giid: String!, $all: Boolean!)"
                  "{\n  installation(giid: $giid) {\n    cameras(allCameras: $all) {\n      ...CommonCameraFragment\n      canChangeEntryExit\n      entryExit\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = await self._doRequest(_body)

        return response["data"]["installation"]["cameras"]

    async def getCapability(self):
        _body = [{
            "operationName": "Capability",
            "variables": {
                "giid": self._giid},
            "query": "query Capability($giid: String!) {\n  installation(giid: $giid) {\n    capability {\n      current\n      gained {\n        capability\n        __typename\n      }\n      __typename\n"
            "}\n    __typename\n  }\n}\n"}]

        response = await self._doRequest(_body)
        return response

    async def chargeSms(self):
        _body = [{
            "operationName": "ChargeSms",
            "variables": {
                "giid": self._giid},
            "query": "query ChargeSms($giid: String!) {\n  installation(giid: $giid) {\n    chargeSms {\n      chargeSmartPlugOnOff\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = await self._doRequest(_body)
        return response

    async def disarmAlarm(self, code):
        _body = [{
            "operationName": "disarm",
            "variables": {
                "giid": self._giid,
                "code": code},
            "query": "mutation disarm($giid: String!, $code: String!) {\n  armStateDisarm(giid: $giid, code: $code)\n}\n"}]

        response = await self._doRequest(_body)
        return response

    async def doorLock(self, deviceLabel):
        _body = [{
            "operationName": "DoorLock",
            "variables": {
                "giid": self._giid,
                "deviceLabel": deviceLabel},
            "query": "mutation DoorLock($giid: String!, $deviceLabel: String!, $input: LockDoorInput!) {\n  DoorLock(giid: $giid, deviceLabel: $deviceLabel, input: $input)\n}\n"}]

        response = await self._doRequest(_body)
        return response

    async def doorUnlook(self, deviceLabel):
        _body = [{
            "operationName": "DoorUnlock",
            "variables": {
                "giid": self._giid,
                "deviceLabel": deviceLabel},
            "input": code,
            "query": "mutation DoorUnlock($giid: String!, $deviceLabel: String!, $input: LockDoorInput!) {\n  DoorUnlock(giid: $giid, deviceLabel: $deviceLabel, input: $input)\n}\n"}]

        response = await self._doRequest(_body)
        return response

    async def getDoorWindow(self):
        _body = [{
            "operationName": "DoorWindow",
            "variables": {
                "giid": self._giid},
            "query": "query DoorWindow($giid: String!) {\n  installation(giid: $giid) {\n    doorWindows {\n      device {\n        deviceLabel\n        __typename\n      }\n      type\n      area\n      state\n"
            "wired\n      reportTime\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = await self._doRequest(_body)

        out = dict()
        for d in response["data"]["installation"]["doorWindows"]:
            name = d["area"]
            out[name] = dict()
            out[name]["state"] = d["state"]
            out[name]["timestamp"] = arrow.get(d["reportTime"]).to('Europe/Stockholm').format("YYYY-MM-DD HH:mm:ss")

        return out

    async def guardianSos(self):
        _body = [{
            "operationName": "GuardianSos",
            "variables": {},
            "query": "query GuardianSos {\n  guardianSos {\n    serverTime\n    sos {\n      fullName\n      phone\n      deviceId\n      deviceName\n      giid\n      type\n      username\n      expireDate\n"
            "warnBeforeExpireDate\n      contactId\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = await self._doRequest(_body)
        return response

    async def isGuardianActivated(self):
        _body = [{
            "operationName": "IsGuardianActivated",
            "variables": {
                "giid": self._giid,
                "featureName": "GUARDIAN"},
            "query": "query IsGuardianActivated($giid: String!, $featureName: String!) {\n  installation(giid: $giid) {\n    activatedFeature {\n      isFeatureActivated(featureName: $featureName)\n      __typename\n"
            "}\n    __typename\n  }\n}\n"}]

        response = await self._doRequest(_body)
        return response

    async def permissions(self):
        _body = [{
            "operationName": "Permissions",
            "variables": {
                "giid": self._giid,
                "email": self._username},
            "query": "query Permissions($giid: String!, $email: String!) {\n  permissions(giid: $giid, email: $email) {\n    accountPermissionsHash\n    name\n    __typename\n  }\n}\n"}]

        response = await self._doRequest(_body)
        return response

    async def pollArmState(self, transactionID, futurestate):
        _body = [{
            "operationName": "pollArmState",
            "variables": {
                "giid": self._giid,
                "transactionId": transactionId,
                "futureState": futureState},
            "query": "query pollArmState($giid: String!, $transactionId: String, $futureState: ArmStateStatusTypes!) {\n  installation(giid: $giid) {\n"
            "armStateChangePollResult(transactionId: $transactionId, futureState: $futureState) {\n      result\n      createTime\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = await self._doRequest(_body)
        return response

    async def pollLockState(self, transactionID, deviceLabel, futureState):
        _body = [{
            "operationName": "pollLockState",
            "variables": {
                "giid": self._giid,
                "transactionId": transactionId,
                "deviceLabel": deviceLabel,
                "futureState": futureState},
            "query": "query pollLockState($giid: String!, $transactionId: String, $deviceLabel: String!, $futureState: DoorLockState!) {\n  installation(giid: $giid) {\n"
            "doorLockStateChangePollResult(transactionId: $transactionId, deviceLabel: $deviceLabel, futureState: $futureState) {\n      result\n      createTime\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = await self._doRequest(_body)
        return response

    async def remainingSms(self):
        _body = [{
            "operationName": "RemainingSms",
            "variables": {
                "giid": self._giid},
            "query": "query RemainingSms($giid: String!) {\n  installation(giid: $giid) {\n    remainingSms\n    __typename\n  }\n}\n"}]

        response = await self._doRequest(_body)
        return response

    async def smartButton(self):
        _body = [{
            "operationName": "SmartButton",
            "variables": {
                "giid": self._giid},
            "query": "query SmartButton($giid: String!) {\n  installation(giid: $giid) {\n    smartButton {\n      entries {\n        smartButtonId\n        icon\n        label\n        color\n        active\n"
            "action {\n          actionType\n          expectedState\n          target {\n            ... on Installation {\n              alias\n              __typename\n            }\n"
            "... on Device {\n              deviceLabel\n              area\n              gui {\n                label\n                __typename\n              }\n              featureStatuses(type: \"SmartPlug\")"
            "{\n                device {\n                  deviceLabel\n                  __typename\n                }\n                ... on SmartPlug {\n                  icon\n                  isHazardous\n"
            "__typename\n                }\n                __typename\n              }\n              __typename\n            }\n            __typename\n          }\n          __typename\n        }\n"
            "__typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = await self._doRequest(_body)
        return response

    async def smartLock(self):
        _body = [{
            "operationName": "SmartLock",
            "variables": {
                "giid": self._giid},
            "query": "query SmartLock($giid: String!) {\n  installation(giid: $giid) {\n    smartLocks {\n      lockStatus\n      doorState\n      lockMethod\n      eventTime\n      doorLockType\n      secureMode\n"
            "device {\n        deviceLabel\n        area\n        __typename\n      }\n      user {\n        name\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = await self._doRequest(_body)
        return response

    async def setSmartPlug(self, deviceLabel, state):
        _body = [{
            "operationName": "UpdateState",
            "variables": {
                "giid": self._giid,
                "deviceLabel": deviceLabel,
                "state": state},
            "query": "mutation UpdateState($giid: String!, $deviceLabel: String!, $state: Boolean!) {\n  SmartPlugSetState(giid: $giid, input: [{deviceLabel: $deviceLabel, state: $state}])}"}]

        response = await self._doRequest(_body)
        return response

    async def getSmartplugState(self, devicelabel):
        _body = [{
            "operationName": "SmartPlug",
            "variables": {
                "giid": self._giid,
                "deviceLabel": deviceLabel},
            "query": "query SmartPlug($giid: String!, $deviceLabel: String!) {\n  installation(giid: $giid) {\n    smartplugs(filter: {deviceLabels: [$deviceLabel]}) {\n      device {\n        deviceLabel\n        area\n"
            "__typename\n      }\n      currentState\n      icon\n      isHazardous\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = await self._doRequest(_body)
        return response

    async def read_smartplug_state(self):
        __body = [{
            "operationName": "SmartPlug",
            "variables": {
                "giid": self._giid},
            "query": "query SmartPlug($giid: String!) {\n  installation(giid: $giid) {\n    smartplugs {\n      device {\n        deviceLabel\n        area\n        __typename\n      }\n      currentState\n      icon\n"
            "isHazardous\n      __typename\n    }\n    __typename\n  }\n}\n"}]

        response = await self._doRequest(__body)
        out = dict()

        for d in response["data"]["installation"]["smartplugs"]:
            name = d["device"]["area"]
            out[name] = d["currentState"]

        return out
