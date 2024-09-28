#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio

import arrow
import structlog
import ujson
from aiohttp import BasicAuth

from API.apihandlers import APIVerisure


class Verisure:

    log = structlog.get_logger(__name__)
    vs = None
    apiHandler = None
    TIME_ZONE = "Europe/Stockholm"
    DATE_FORMAT = "YYYY-MM-DD HH:mm:ss"

    def __init__(self, mfa: bool, username, password):
        self._mfa = mfa
        self._username = username
        self._giid = None
        self.graphqlUrls = ['https://m-api01.verisure.com/graphql',
                            'https://m-api02.verisure.com/graphql']

    @classmethod
    async def create(cls, username, password):
        try:
            if cls.vs is None:
                cls.vs = cls(mfa=False, username=username, password=password)
                if cls.apiHandler is None:
                    cls.apiHandler = await APIVerisure.create(name="Verisure",
                                                              tokenFileName="/home/staffan/olis/olis_verisure/tokenfile.txt",
                                                              lastSessionFileName="/home/staffan/olis/olis_verisure/lastsessionfile.txt",
                                                              headers={"Content-Type": "application/json",
                                                                       "Host": "m-api01.verisure.com",
                                                                       "Cache-Control": "no-cache",
                                                                       "APPLICATION_ID": "Python"},
                                                              auth=BasicAuth(username, password),
                                                              loginUrls=["https://m-api01.verisure.com/auth/login",
                                                                         "https://m-api02.verisure.com/auth/login"],
                                                              logoutUrls=['https://m-api01.verisure.com/auth/logout',
                                                                          'https://m-api02.verisure.com/auth/logout'],
                                                              refreshUrls=['https://m-api01.verisure.com/auth/token',
                                                                           'https://m-api02.verisure.com/auth/token'],
                                                              RETRIES=5,
                                                              RETRY_DELAY=300,
                                                              THROTTLE_DELAY=0,
                                                              THROTTLE_ERROR_DELAY=3*60*60)

            await cls.vs.getAllInstallations()
            return cls.vs

        except Exception as e:
            cls.log.error(f"Exception in create", error=e)

    async def logout(self):
        await self.apiHandler.logout()

    async def getAllInstallations(self):
        _body = [{"operationName": "fetchAllInstallations",
                  "variables": {
                      "email": self._username
                  },
                  "query": """
                query fetchAllInstallations($email: String!) {
                account(email: $email) {
                    installations {
                    giid
                    alias
                    customerType
                    dealerId
                    subsidiary
                    pinCodeLength
                    locale
                    address {
                        street
                        city
                        postalNumber
                        __typename
                    }
                    __typename
                    }
                    __typename
                }
                }
            """
                  }]

        response = await self.apiHandler.doSession(method="POST", url=self.graphqlUrls, data=ujson.dumps(list(_body)))

        for d in response["data"]["account"]["installations"]:
            self._giid = d["giid"]

    async def getBatteryProcessStatus(self):
        if self._giid is None:
            await self.vs.getAllInstallations()

        _body = [{
            "operationName": "batteryDevices",
            "variables": {
                "giid": self._giid
            },
            "query": """
                query batteryDevices($giid: String!) {
                installation(giid: $giid) {
                    batteryDevices {
                    device {
                        area
                        deviceLabel
                        gui {
                        picture
                        label
                        __typename
                        }
                        __typename
                    }
                    batteryCount
                    recommendedToChange
                    batteryTrend
                    estimatedRemainingBatteryLifetime
                    batteryType
                    batteryHealth
                    __typename
                    }
                    __typename
                }
                }
            """
        }]

        response = await self.apiHandler.doSession(method="POST", url=self.graphqlUrls, data=ujson.dumps(list(_body)))

        out = {}
        for d in response["data"]["installation"]["batteryDevices"]:
            name = f"{d['device']['area']}/{d['device']['gui']['label']}"
            out[name] = {"batteryHealth": d["batteryHealth"],
                         "estimatedRemainingBatteryLifetime": d["estimatedRemainingBatteryLifetime"],
                         "recommendedToChange": d["recommendedToChange"]}

        return out

    async def getClimate(self):
        if self._giid is None:
            await self.vs.getAllInstallations()

        _body = [{
            "operationName": "Climate",
            "variables": {
                "giid": self._giid
            },
            "query": """
                query Climate($giid: String!) {
                installation(giid: $giid) {
                    climates {
                    device {
                        deviceLabel
                        area
                        gui {
                        label
                        support
                        __typename
                        }
                        __typename
                    }
                    humidityEnabled
                    humidityTimestamp
                    humidityValue
                    temperatureTimestamp
                    temperatureValue
                    supportsThresholdSettings
                    thresholds {
                        aboveMaxAlert
                        belowMinAlert
                        sensorType
                        __typename
                    }
                    __typename
                    }
                    __typename
                }
                }
            """
        }]

        response = await self.apiHandler.doSession(method="POST", url=self.graphqlUrls, data=ujson.dumps(list(_body)))

        out = {}
        for d in response["data"]["installation"]["climates"]:
            name = d["device"]["area"] + "/" + d["device"]["gui"]["label"]
            out[name] = {"temperature": d["temperatureValue"],
                         "timestamp": arrow.get(d["temperatureTimestamp"]).to(self.TIME_ZONE).format(self.DATE_FORMAT)}

        return out

    async def userTracking(self):
        if self._giid is None:
            await self.vs.getAllInstallations()

        _body = [{
            "operationName": "userTrackings",
            "variables": {
                "giid": self._giid
            },
            "query": """
                query userTrackings($giid: String!) {
                installation(giid: $giid) {
                    userTrackings {
                    isCallingUser
                    webAccount
                    status
                    xbnContactId
                    currentLocationName
                    deviceId
                    name
                    initials
                    currentLocationTimestamp
                    deviceName
                    currentLocationId
                    __typename
                    }
                    __typename
                }
                }
            """
        }]

        response = await self.apiHandler.doSession(method="POST", url=self.graphqlUrls, data=ujson.dumps(list(_body)))

        out = {}
        for d in response["data"]["installation"]["userTrackings"]:
            name = d["name"]

            if (d["currentLocationName"] is not None):
                out[name] = {"currentLocationName": d["currentLocationName"],
                             "timestamp": arrow.get(d["currentLocationTimestamp"]).to(self.TIME_ZONE).format(self.DATE_FORMAT)}
            else:
                out[name] = {"currentLocationName": "None",
                             "timestamp": '1970-01-01 00:00:00'}

        return out

    async def getAllCardConfig(self):
        if self._giid is None:
            await self.vs.getAllInstallations()

        _body = [{
            "operationName": "AllCardConfig",
            "variables": {
                "giid": self._giid
            },
            "query": """
                query AllCardConfig($giid: String!) {
                installation(giid: $giid) {
                    allCardConfig {
                    cardName
                    selection
                    visible
                    items {
                        id
                        visible
                        __typename
                    }
                    __typename
                    }
                    __typename
                }
                }
            """
        }]

        response = await self.apiHandler.doSession(method="POST", url=self.graphqlUrls, data=ujson.dumps(list(_body)))
        return response

    async def getVacationMode(self):
        if self._giid is None:
            await self.vs.getAllInstallations()

        _body = [{
            "operationName": "VacationMode",
            "variables": {
                "giid": self._giid
            },
            "query": """
                query VacationMode($giid: String!) {
                installation(giid: $giid) {
                    vacationMode {
                    isAllowed
                    turnOffPetImmunity
                    fromDate
                    toDate
                    temporaryContactName
                    temporaryContactPhone
                    active
                    __typename
                    }
                    __typename
                }
                }
            """
        }]

        response = await self.apiHandler.doSession(method="POST", url=self.graphqlUrls, data=ujson.dumps(list(_body)))

        out = {}
        name = response["data"]["installation"]["vacationMode"]["__typename"]
        out[name] = {"active": response["data"]["installation"]["vacationMode"]["active"]}

        _fromDate = response["data"]["installation"]["vacationMode"]["fromDate"]
        out[name]["fromDate"] = arrow.get(_fromDate).to(self.TIME_ZONE).format(self.DATE_FORMAT) if _fromDate is not None else None

        _toDate = response["data"]["installation"]["vacationMode"]["fromDate"]
        out[name]["toDate"] = arrow.get(_toDate).to(self.TIME_ZONE).format(self.DATE_FORMAT) if _toDate is not None else None

        out[name]["contactName"] = response["data"]["installation"]["vacationMode"]["temporaryContactName"]
        out[name]["contactPhone"] = response["data"]["installation"]["vacationMode"]["temporaryContactPhone"]

        return out

    async def getCommunication(self):
        if self._giid is None:
            await self.vs.getAllInstallations()

            _body = [{
                "operationName": "communicationState",
                "variables": {
                    "giid": self._giid
                },
                "query": """
                query communicationState($giid: String!) {
                installation(giid: $giid) {
                    communicationState {
                    hardwareCarrierType
                    result
                    mediaType
                    device {
                        deviceLabel
                        area
                        gui {
                        label
                        __typename
                        }
                        __typename
                    }
                    testDate
                    __typename
                    }
                    __typename
                }
                }
            """
            }]

        response = await self.apiHandler.doSession(method="POST", url=self.graphqlUrls, data=ujson.dumps(list(_body)))

        out = {}
        for d in response["data"]["installation"]["communicationState"]:
            name = d["device"]["area"]
            if name not in out:
                out[name] = list()

            part = {"result": d["result"],
                    "hardwareCarrierType": d["hardwareCarrierType"],
                    "mediaType": d["mediaType"],
                    "timestamp": arrow.get(d["testDate"]).to(self.TIME_ZONE).format(self.DATE_FORMAT)}

            out[name].append(part)

        return out

    async def getEventLogCategories(self):
        if self._giid is None:
            await self.vs.getAllInstallations()

        _body = [{
                "operationName": "EventLogCategories",
                "variables": {
                    "giid": self._giid
                },
                "query": """
                query EventLogCategories($giid: String!) {
                installation(giid: $giid) {
                    notificationCategoryFilter
                    __typename
                }
                }
            """
            }]

        response = await self.apiHandler.doSession(method="POST", url=self.graphqlUrls, data=ujson.dumps(list(_body)))

        return response["data"]["installation"]["notificationCategoryFilter"]

    async def getEventLog(self, fromDate, toDate, eventCategories):
        if self._giid is None:
            await self.vs.getAllInstallations()

        _body = [{
            "operationName": "EventLog",
            "variables": {
                "hideNotifications": True,
                "offset": 0,
                "pagesize": 255,
                "eventCategories": eventCategories,
                "giid": self._giid,
                "eventContactIds": [],
                "fromDate": arrow.get(fromDate).format("YYYYMMDD"),
                "toDate": arrow.get(toDate).format("YYYYMMDD")
            },
            "query": """
                query EventLog($giid: String!, $offset: Int!, $pagesize: Int!, $eventCategories: [String], $fromDate: String, $toDate: String, $eventContactIds: [String]) {
                installation(giid: $giid) {
                    eventLog(
                    offset: $offset, 
                    pagesize: $pagesize, 
                    eventCategories: $eventCategories, 
                    eventContactIds: $eventContactIds, 
                    fromDate: $fromDate, 
                    toDate: $toDate
                    ) {
                    moreDataAvailable
                    pagedList {
                        device {
                        deviceLabel
                        area
                        gui {
                            label
                            __typename
                        }
                        __typename
                        }
                        arloDevice {
                        name
                        __typename
                        }
                        gatewayArea
                        eventType
                        eventCategory
                        eventId
                        eventTime
                        userName
                        armState
                        userType
                        climateValue
                        sensorType
                        eventCount
                        __typename
                    }
                    __typename
                    }
                    __typename
                }
                }
            """
        }]

        response = await self.apiHandler.doSession(method="POST", url=self.graphqlUrls, data=ujson.dumps(list(_body)))

        out = {}
        for d in response["data"]["installation"]["eventLog"]["pagedList"]:
            eventCategory = d["eventCategory"]
            if eventCategory not in out:
                out[eventCategory] = list()

            part = {"device": d["device"]["area"],
                    "timestamp": arrow.get(d["eventTime"]).to(self.TIME_ZONE).format(self.DATE_FORMAT)}
            if eventCategory in ["ARM", "DISARM"]:
                part["user"] = d["userName"]
                part["armState"] = d["armState"]
            elif eventCategory == "INTRUSION":
                part["armState"] = d["armState"]

            out[eventCategory].append(part)

        return out

    async def getInstallation(self):
        if self._giid is None:
            await self.vs.getAllInstallations()

        _body = [{
            "operationName": "Installation",
            "variables": {
                "giid": self._giid},
            "query": """
            query Installation($giid: String!) {
              installation(giid: $giid) {
                alias
                pinCodeLength
                customerType
                notificationCategoryFilter
                userNotificationCategories
                doorWindowReportState
                dealerId
                isOperatorMonitorable
                removeInstallationNotAllowed
                installationNumber
                editInstallationAddressNotAllowed
                locale
                editGuardInformationAllowed
                __typename
              }
            }
        """
        }]

        response = await self.apiHandler.doSession(method="POST", url=self.graphqlUrls, data=ujson.dumps(list(_body)))

        return response["data"]["installation"]

    async def getUsers(self):
        if self._giid is None:
            await self.vs.getAllInstallations()

        _body = [{
            "operationName": "Users",
            "variables": {
                "giid": self._giid},
            "query": """
            fragment Users on User {
              profile
              accessCodeChangeInProgress
              hasDoorLockTag
              pendingInviteProfile
              relationWithInstallation
              contactId
              accessCodeSetTransactionId
              userIndex
              name
              hasTag
              hasDoorLockPin
              hasDigitalSignatureKey
              email
              mobilePhoneNumber
              callOrder
              tagColor
              phoneNumber
              webAccount
              doorLockUser
              alternativePhoneNumber
              keyHolder
              hasCode
              pendingInviteStatus
              xbnContactId
              userAccessTimeLimitation {
                activeOnMonday
                activeOnTuesday
                activeOnWednesday
                activeOnThursday
                activeOnFriday
                activeOnSaturday
                activeOnSunday
                fromLocalDate
                toLocalDate
                toLocalTimeOfDay
                fromLocalTimeOfDay
                __typename
              }
              __typename
            }
            
            query Users($giid: String!) {
              users(giid: $giid) {
                ...Users
                notificationTypes
                notificationSettings {
                  contactFilter {
                    contactName
                    filterContactId
                    __typename
                  }
                  notificationCategory
                  notificationType
                  optionFilter
                  __typename
                }
                keyfob {
                  device {
                    deviceLabel
                    area
                    __typename
                  }
                  __typename
                }
                __typename
              }
            }
        """
        }]

        response = await self.apiHandler.doSession(method="POST", url=self.graphqlUrls, data=ujson.dumps(list(_body)))

        return response["data"]["users"]

    async def getVacationModeAndPetSetting(self):
        if self._giid is None:
            await self.vs.getAllInstallations()

        _body = [{
            "operationName": "VacationModeAndPetSettings",
            "variables": {
                "giid": self._giid},
            "query": """
            query VacationModeAndPetSettings($giid: String!) {
              installation(giid: $giid) {
                vacationMode {
                  isAllowed
                  turnOffPetImmunity
                  fromDate
                  toDate
                  temporaryContactName
                  temporaryContactPhone
                  active
                  __typename
                }
                petSettings {
                  devices {
                    area
                    deviceLabel
                    petSettingsActive
                    __typename
                  }
                  __typename
                }
                __typename
              }
            }
        """
        }]

        response = await self.apiHandler.doSession(method="POST", url=self.graphqlUrls, data=ujson.dumps(list(_body)))

        out = {"petSettings": {}}
        for d in response["data"]["installation"]["petSettings"]["devices"]:
            area = d["area"]
            out["petSettings"][area] = d["petSettingsActive"]

        name = response["data"]["installation"]["vacationMode"]["__typename"]
        out[name] = {"active": response["data"]["installation"]["vacationMode"]["active"]}

        _fromDate = response["data"]["installation"]["vacationMode"]["fromDate"]
        out[name]["fromDate"] = arrow.get(_fromDate).to(self.TIME_ZONE).format(self.DATE_FORMAT) if _fromDate is not None else None

        _toDate = response["data"]["installation"]["vacationMode"]["fromDate"]
        out[name]["toDate"] = arrow.get(_toDate).to(self.TIME_ZONE).format(self.DATE_FORMAT) if _toDate is not None else None

        out[name]["contactName"] = response["data"]["installation"]["vacationMode"]["temporaryContactName"]
        out[name]["contactPhone"] = response["data"]["installation"]["vacationMode"]["temporaryContactPhone"]
        out[name]["turnOffPetImmunity"] = response["data"]["installation"]["vacationMode"]["turnOffPetImmunity"]

        return out

    async def getPetType(self):
        if self._giid is None:
            await self.vs.getAllInstallations()

        _body = [{
            "operationName": "GetPetType",
            "variables": {
                "giid": self._giid},
            "query": """
                query GetPetType($giid: String!) {
                installation(giid: $giid) {
                    pettingSettings {
                    petType
                    __typename
                    }
                    __typename
                }
                }
            """
        }]

        response = await self.apiHandler.doSession(method="POST", url=self.graphqlUrls, data=ujson.dumps(list(_body)))

        return response["data"]["installation"]["pettingSettings"]["petType"]

    async def getCentralUnit(self):
        if self._giid is None:
            await self.vs.getAllInstallations()

        _body = [{
            "operationName": "centralUnits",
            "variables": {
                "giid": self._giid},
            "query": """
                    query centralUnits($giid: String!) {
                    installation(giid: $giid) {
                        centralUnits {
                        macAddress {
                            macAddressEthernet
                            __typename
                        }
                        device {
                            deviceLabel
                            area
                            gui {
                            label
                            support
                            __typename
                            }
                            __typename
                        }
                        __typename
                        }
                        __typename
                    }
                    }
                """
        }]

        response = await self.apiHandler.doSession(method="POST", url=self.graphqlUrls, data=ujson.dumps(list(_body)))

        out = {}
        for d in response["data"]["installation"]["centralUnits"]:
            name = d["device"]["area"]
            out[name] = {"label": d["device"]["gui"]["label"],
                         "macAddressEthernet": d["macAddress"]["macAddressEthernet"]}

        return out

    async def getDevices(self):
        if self._giid is None:
            await self.vs.getAllInstallations()

        _body = [{
            "operationName": "Devices",
            "variables": {
                "giid": self._giid},
            "query": """
                    fragment DeviceFragment on Device {
                    deviceLabel
                    area
                    capability
                    gui {
                        support
                        picture
                        deviceGroup
                        sortOrder
                        label
                        __typename
                    }
                    monitoring {
                        operatorMonitored
                        __typename
                    }
                    __typename
                    }
                    
                    query Devices($giid: String!) {
                    installation(giid: $giid) {
                        devices {
                        ...DeviceFragment
                        canChangeEntryExit
                        entryExit
                        __typename
                        }
                        __typename
                    }
                    }
                """
        }]

        response = await self.apiHandler.doSession(method="POST", url=self.graphqlUrls, data=ujson.dumps(list(_body)))

        out = []
        for d in response["data"]["installation"]["devices"]:
            label = d["gui"]["label"]
            namn = d["area"]
            out.append(f"{namn}/{label}")
            # out[label] = {"namn": d["area"], "label": d["gui"]["label"]}
            # out[name][""] = d["currentLocationName"]
            # out[name]["timestamp"] = arrow.get(d["currentLocationTimestamp"]).format("YYYY-MM-DD HH:mm")

        return out

    async def setArmStatusAway(self, code):
        if self._giid is None:
            await self.vs.getAllInstallations()

        _body = [{
            "operationName": "armAway",
            "variables": {
                "giid": self._giid,
                "code": code},
            "query": """
                mutation armAway($giid: String!, $code: String!) {
                armStateArmAway(giid: $giid, code: $code)
                }
            """
        }]

        response = await self.apiHandler.doSession(method="POST", url=self.graphqlUrls, data=ujson.dumps(list(_body)))
        return response

    async def setArmStatusHome(self, code):
        if self._giid is None:
            await self.vs.getAllInstallations()

        _body = [{
            "operationName": "armHome",
            "variables": {
                "giid": self._giid,
                "code": code},
            "query": """
                    mutation armHome($giid: String!, $code: String!) {
                    armStateArmHome(giid: $giid, code: $code)
                    }
                """
        }]

        response = await self.apiHandler.doSession(method="POST", url=self.graphqlUrls, data=ujson.dumps(list(_body)))
        return response

    async def getArmState(self):
        if self._giid is None:
            await self.vs.getAllInstallations()

        _body = [{
            "operationName": "ArmState",
            "variables": {
                "giid": self._giid},
            "query": """
                query ArmState($giid: String!) {
                installation(giid: $giid) {
                    armState {
                    type
                    statusType
                    date
                    name
                    changedVia
                    __typename
                    }
                    __typename
                }
                }
            """
        }]

        response = await self.apiHandler.doSession(method="POST", url=self.graphqlUrls, data=ujson.dumps(list(_body)))

        out = {}
        name = response["data"]["installation"]["armState"]["__typename"]
        out[name] = {"statusType": response["data"]["installation"]["armState"]["statusType"],
                     "changedVia": response["data"]["installation"]["armState"]["changedVia"],
                     "timestamp": arrow.get(response["data"]["installation"]["armState"]["date"]).to(self.TIME_ZONE).format(self.DATE_FORMAT)}

        return out

    async def getBroadbandStatus(self):
        if self._giid is None:
            await self.vs.getAllInstallations()

        _body = [{
            "operationName": "Broadband",
            "variables": {
                "giid": self._giid
            },
            "query": """
                query Broadband($giid: String!) {
                installation(giid: $giid) {
                    broadband {
                    testDate
                    isBroadbandConnected
                    __typename
                    }
                    __typename
                }
                }
            """
        }]

        response = await self.apiHandler.doSession(method="POST", url=self.graphqlUrls, data=ujson.dumps(list(_body)))

        out = {}
        name = response["data"]["installation"]["broadband"]["__typename"]
        out[name] = {"connected": response["data"]["installation"]["broadband"]["isBroadbandConnected"],
                     "timestamp": arrow.get(response["data"]["installation"]["broadband"]["testDate"]).to(self.TIME_ZONE).format(self.DATE_FORMAT)}

        return out

    async def getCamera(self):
        if self._giid is None:
            await self.vs.getAllInstallations()

        _body = [{
            "operationName": "Camera",
            "variables": {
                "giid": self._giid,
                "all": True
            },
            "query": """
                        query Camera($giid: String!, $all: Boolean!) {
                        installation(giid: $giid) {
                            cameras(allCameras: $all) {
                            ...CommonCameraFragment
                            canChangeEntryExit
                            entryExit
                            }
                        }
                        }

                        fragment CommonCameraFragment on Camera {
                        device {
                            deviceLabel
                            area
                            capability
                            gui {
                            label
                            support
                            __typename
                            }
                            __typename
                        }
                        type
                        latestImageCapture
                        motionDetectorMode
                        imageCaptureAllowedByArmstate
                        accelerometerMode
                        supportedBlockSettingValues
                        imageCaptureAllowed
                        initiallyConfigured
                        imageResolution
                        hasMotionSupport
                        totalUnseenImages
                        canTakePicture
                        takePictureProblems
                        canStream
                        streamProblems
                        videoRecordSettingAllowed
                        microphoneSettingAllowed
                        supportsFullDuplexAudio
                        fullDuplexAudioProblems
                        cvr {
                            supported
                            recording
                            availablePlaylistDays
                            __typename
                        }
                        __typename
                        }
                    """
        }]

        response = await self.apiHandler.doSession(method="POST", url=self.graphqlUrls, data=ujson.dumps(list(_body)))

        return response["data"]["installation"]["cameras"]

    async def getCapability(self):
        if self._giid is None:
            await self.vs.getAllInstallations()

        _body = [{
            "operationName": "Capability",
            "variables": {
                "giid": self._giid
            },
            "query": """
                query Capability($giid: String!) {
                  installation(giid: $giid) {
                    capability {
                      current
                      gained {
                        capability
                      }
                    }
                  }
                }
            """
        }]

        response = await self.apiHandler.doSession(method="POST", url=self.graphqlUrls, data=ujson.dumps(list(_body)))

        return response

    async def chargeSms(self):
        if self._giid is None:
            await self.vs.getAllInstallations()

        _body = [{
            "operationName": "ChargeSms",
            "variables": {
                "giid": self._giid
            },
            "query": """
                query ChargeSms($giid: String!) {
                  installation(giid: $giid) {
                    chargeSms {
                      chargeSmartPlugOnOff
                    }
                  }
                }
            """
        }]

        response = await self.apiHandler.doSession(method="POST", url=self.graphqlUrls, data=ujson.dumps(list(_body)))

        return response

    async def disarmAlarm(self, code):
        if self._giid is None:
            await self.vs.getAllInstallations()

        _body = [{
            "operationName": "disarm",
            "variables": {
                "giid": self._giid,
                "code": code
            },
            "query": """
                mutation disarm($giid: String!, $code: String!) {
                  armStateDisarm(giid: $giid, code: $code)
                }
            """
        }]

        response = await self.apiHandler.doSession(method="POST", url=self.graphqlUrls, data=ujson.dumps(list(_body)))

        return response

    async def doorLock(self, deviceLabel):
        if self._giid is None:
            await self.vs.getAllInstallations()

        _body = [{
            "operationName": "DoorLock",
            "variables": {
                "giid": self._giid,
                "deviceLabel": deviceLabel
            },
            "query": """
                mutation DoorLock($giid: String!, $deviceLabel: String!, $input: LockDoorInput!) {
                  DoorLock(giid: $giid, deviceLabel: $deviceLabel, input: $input)
                }
            """
        }]

        response = await self.apiHandler.doSession(method="POST", url=self.graphqlUrls, data=ujson.dumps(list(_body)))

        return response

    async def doorUnlook(self, deviceLabel, code):
        if self._giid is None:
            await self.vs.getAllInstallations()

        _body = [{
            "operationName": "DoorUnlock",
            "variables": {
                "giid": self._giid,
                "deviceLabel": deviceLabel
            },
            "input": code,
            "query": """
                mutation DoorUnlock($giid: String!, $deviceLabel: String!, $input: LockDoorInput!) {
                  DoorUnlock(giid: $giid, deviceLabel: $deviceLabel, input: $input)
                }
            """
        }]

        response = await self.apiHandler.doSession(method="POST", url=self.graphqlUrls, data=ujson.dumps(list(_body)))

        return response

    async def getDoorWindow(self):
        if self._giid is None:
            await self.vs.getAllInstallations()

        _body = [{
            "operationName": "DoorWindow",
            "variables": {
                "giid": self._giid
            },
            "query": """
                query DoorWindow($giid: String!) {
                installation(giid: $giid) {
                    doorWindows {
                    device {
                        deviceLabel
                        __typename
                    }
                    type
                    area
                    state
                    wired
                    reportTime
                    __typename
                    }
                    __typename
                }
                }
            """
        }]

        response = await self.apiHandler.doSession(method="POST", url=self.graphqlUrls, data=ujson.dumps(list(_body)))

        out = {}
        for d in response["data"]["installation"]["doorWindows"]:
            name = d["area"]
            out[name] = {'state': d['state'],
                         "timestamp": arrow.get(d["reportTime"]).to(self.TIME_ZONE).format(self.DATE_FORMAT)}

        return out

    async def guardianSos(self):
        if self._giid is None:
            await self.vs.getAllInstallations()

        _body = [{
            "operationName": "GuardianSos",
            "variables": {},
            "query": """
                    query GuardianSos {
                    guardianSos {
                        serverTime
                        sos {
                        fullName
                        phone
                        deviceId
                        deviceName
                        giid
                        type
                        username
                        expireDate
                        warnBeforeExpireDate
                        contactId
                        __typename
                        }
                        __typename
                    }
                    }
                """
        }]

        response = await self.apiHandler.doSession(method="POST", url=self.graphqlUrls, data=ujson.dumps(list(_body)))

        return response

    async def isGuardianActivated(self):
        if self._giid is None:
            await self.vs.getAllInstallations()

        _body = [{
            "operationName": "IsGuardianActivated",
            "variables": {
                "giid": self._giid,
                "featureName": "GUARDIAN"
            },
            "query": """
                query IsGuardianActivated($giid: String!, $featureName: String!) {
                installation(giid: $giid) {
                    activatedFeature {
                    isFeatureActivated(featureName: $featureName)
                    __typename
                    }
                    __typename
                }
                }
            """
        }]

        response = await self.apiHandler.doSession(method="POST", url=self.graphqlUrls, data=ujson.dumps(list(_body)))

        return response

    async def permissions(self):
        if self._giid is None:
            await self.vs.getAllInstallations()

        _body = [{
            "operationName": "Permissions",
            "variables": {
                "giid": self._giid,
                "email": self._username
            },
            "query": """
                query Permissions($giid: String!, $email: String!) {
                permissions(giid: $giid, email: $email) {
                    accountPermissionsHash
                    name
                    __typename
                }
                }
            """
        }]

        response = await self.apiHandler.doSession(method="POST", url=self.graphqlUrls, data=ujson.dumps(list(_body)))

        return response

    async def pollArmState(self, transactionID, futureState):
        if self._giid is None:
            await self.vs.getAllInstallations()

        _body = [{
            "operationName": "pollArmState",
            "variables": {
                "giid": self._giid,
                "transactionId": transactionID,
                "futureState": futureState
            },
            "query": """
                query pollArmState($giid: String!, $transactionId: String, $futureState: ArmStateStatusTypes!) {
                installation(giid: $giid) {
                    armStateChangePollResult(transactionId: $transactionId, futureState: $futureState) {
                    result
                    createTime
                    __typename
                    }
                    __typename
                }
                }
            """
        }]

        response = await self.apiHandler.doSession(method="POST", url=self.graphqlUrls, data=ujson.dumps(list(_body)))

        return response

    async def pollLockState(self, transactionID, deviceLabel, futureState):
        if self._giid is None:
            await self.vs.getAllInstallations()

        _body = [{
            "operationName": "pollLockState",
            "variables": {
                "giid": self._giid,
                "transactionId": transactionID,
                "deviceLabel": deviceLabel,
                "futureState": futureState
            },
            "query": """
                query pollLockState($giid: String!, $transactionId: String, $deviceLabel: String!, $futureState: DoorLockState!) {
                installation(giid: $giid) {
                    doorLockStateChangePollResult(transactionId: $transactionId, deviceLabel: $deviceLabel, futureState: $futureState) {
                    result
                    createTime
                    __typename
                    }
                    __typename
                }
                }
            """
        }]

        response = await self.apiHandler.doSession(method="POST", url=self.graphqlUrls, data=ujson.dumps(list(_body)))

        return response

    async def remainingSms(self):
        if self._giid is None:
            await self.vs.getAllInstallations()

        _body = [{
            "operationName": "RemainingSms",
            "variables": {
                "giid": self._giid
            },
            "query": """
                query RemainingSms($giid: String!) {
                installation(giid: $giid) {
                    remainingSms
                    __typename
                }
                }
            """
        }]

        response = await self.apiHandler.doSession(method="POST", url=self.graphqlUrls, data=ujson.dumps(list(_body)))

        return response

    async def smartButton(self):
        if self._giid is None:
            await self.vs.getAllInstallations()

        _body = [{
            "operationName": "SmartButton",
            "variables": {
                "giid": self._giid
            },
            "query": """
                    query SmartButton($giid: String!) {
                    installation(giid: $giid) {
                        smartButton {
                        entries {
                            smartButtonId
                            icon
                            label
                            color
                            active
                            action {
                            actionType
                            expectedState
                            target {
                                ... on Installation {
                                alias
                                __typename
                                }
                                ... on Device {
                                deviceLabel
                                area
                                gui {
                                    label
                                    __typename
                                }
                                featureStatuses(type: "SmartPlug") {
                                    device {
                                    deviceLabel
                                    __typename
                                    }
                                    ... on SmartPlug {
                                    icon
                                    isHazardous
                                    __typename
                                    }
                                    __typename
                                }
                                __typename
                                }
                                __typename
                            }
                            __typename
                            }
                            __typename
                        }
                        __typename
                        }
                        __typename
                    }
                    }
                """
        }]

        response = await self.apiHandler.doSession(method="POST", url=self.graphqlUrls, data=ujson.dumps(list(_body)))

        return response

    async def smartLock(self):
        if self._giid is None:
            await self.vs.getAllInstallations()

        _body = [{
            "operationName": "SmartLock",
            "variables": {
                "giid": self._giid
            },
            "query": """
                query SmartLock($giid: String!) {
                installation(giid: $giid) {
                    smartLocks {
                    lockStatus
                    doorState
                    lockMethod
                    eventTime
                    doorLockType
                    secureMode
                    device {
                        deviceLabel
                        area
                        __typename
                    }
                    user {
                        name
                        __typename
                    }
                    __typename
                    }
                    __typename
                }
                }
            """
        }]

        response = await self.apiHandler.doSession(method="POST", url=self.graphqlUrls, data=ujson.dumps(list(_body)))

        return response

    async def setSmartPlug(self, deviceLabel, state):
        if self._giid is None:
            await self.vs.getAllInstallations()

        _body = [{
            "operationName": "UpdateState",
            "variables": {
                "giid": self._giid,
                "deviceLabel": deviceLabel,
                "state": state
            },
            "query": """
                mutation UpdateState($giid: String!, $deviceLabel: String!, $state: Boolean!) {
                SmartPlugSetState(giid: $giid, input: [{deviceLabel: $deviceLabel, state: $state}]) {
                    giid
                    input {
                    deviceLabel
                    state
                    }
                    __typename
                }
                }
            """
        }]

        response = await self.apiHandler.doSession(method="POST", url=self.graphqlUrls, data=ujson.dumps(list(_body)))

        return response

    async def getSmartplugState(self, devicelabel):
        if self._giid is None:
            await self.vs.getAllInstallations()

        _body = [{
            "operationName": "SmartPlug",
            "variables": {
                "giid": self._giid,
                "deviceLabel": devicelabel
            },
            "query": """
                query SmartPlug($giid: String!, $deviceLabel: String!) {
                installation(giid: $giid) {
                    smartplugs(filter: {deviceLabels: [$deviceLabel]}) {
                    device {
                        deviceLabel
                        area
                        __typename
                    }
                    currentState
                    icon
                    isHazardous
                    __typename
                    }
                    __typename
                }
                }
            """
        }]

        response = await self.apiHandler.doSession(method="POST", url=self.graphqlUrls, data=ujson.dumps(list(_body)))

        return response

    async def read_smartplug_state(self):
        if self._giid is None:
            await self.vs.getAllInstallations()

        _body = [{
            "operationName": "SmartPlug",
            "variables": {
                "giid": self._giid
            },
            "query": """
                query SmartPlug($giid: String!) {
                installation(giid: $giid) {
                    smartplugs {
                    device {
                        deviceLabel
                        area
                        __typename
                    }
                    currentState
                    icon
                    isHazardous
                    __typename
                    }
                    __typename
                }
                }
            """
        }]

        response = await self.apiHandler.doSession(method="POST", url=self.graphqlUrls, data=ujson.dumps(list(_body)))

        out = {}
        for d in response["data"]["installation"]["smartplugs"]:
            name = d["device"]["area"]
            out[name] = d["currentState"]

        return out
