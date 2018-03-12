import numpy as np
import matplotlib.pyplot as plt
import math
import sys

# Distance and area unit is in meters
# Time is in seconds
#-------------------------------Constants and Global Variables-------------------------------------------

grid={}#Dictionary having "center of the 10x10 square as Key" and "Shadowing as Value"
subscriberInfo={}#Dictionary containing "Active" User Information Key is USER ID, Values are (User Location X coordinate, User Location Y coordinate, Distance from Base Station), Call Duration, Call Attempt Retry, In-Call Retry due to Low SINR)
active_user_id=[]#List of active Users
lowRSLUser=[]#List of Users having RSL lower than Minimum Required RSL

#Performance Counters
successfullCallCompletion=0#Number of Succesfully completed call
numberOfActiveCalls=0#Number of Users Occuping Traffic Channels
numberOfBlockedCalls=0#Number of Calls Blocked due to Capacity
numberOfDroppedCalls=0#Number of Calls Dropped due to Low SINR
numberOfBlockedCallsCoverage=0#Number of Calls Blocked due to Low Pilot RSL
numberOfCallAttempts=0#Number of First Call Attempt, does not count Retry
numberOfCallAttemptsWithRetry=0#Number of Total Call Attempts including Retry
cellRadius=0#Distance of Most distant Active User from Base Station

CELL_RADIUS = 10000 # in meters
NUMBER_OF_USERS=1000 # This can be changed to generate various users
LAMBDA = 6 # Given, average number of calls by a user
CALL_DURATION = 60 # Given, Average Call Duration
PROB_OF_CALLING = 1/600 # 6 calls an hour (3600 seconds)
NUMBER_OF_TRAFFIC_CHANNELS = 56# Number of available Traffic Channels
BSTXPOWER = 42# dBm, Base Station output power in dBm
CONNECTORLOSS = 2.1 # dB, Cable and Connector loss
BSANTENNAGAIN = 12.1# dB, Base station Antenna Gain
MAX_EIRP = BSTXPOWER - CONNECTORLOSS + BSANTENNAGAIN # 52 dBm, Maximum allowable EIRP
pilotEIRP=MAX_EIRP #I nitialise Pilot Power with Max power (52dBm)
MIN_EIRP = 30 # dBm, Maximum allowable EIRP 30 dBm
Delta_EIRP_Pilot =  0.5 # dB
Cd = 20 # Number of channels above which the Pilot power to be decreased
Ci = 15 # Number of channels below which the Pilot power to be decreased
MIN_PILOT_RSL = -107 # dBm, Minimum required Pilot channel received power in order to make a call
PROCESSINGGAIN = 20 # dB, Calculated from Data Rate and Carrier Bandwidth, value comes to 20 dB
NOISELEVEL = -110 # dBm, Noise level
REQUIRED_SINR = 6 # dB, Minimum required SINR to successfully continue the call


#-------------------------------User Location-------------------------------------------

def userLocation():#Generates Random Location of the User
    distance_from_basestation = CELL_RADIUS*np.sqrt(np.random.rand()) # Square root is used to Uniformly distribute points over the area of circle
    theta = np.random.uniform(0.0, 2.0*np.pi) # Any value between 0 to 2-PI
    userXCoordinate = distance_from_basestation * np.cos(theta)
    userYCoordinate = distance_from_basestation * np.sin(theta)
    return ((userXCoordinate, userYCoordinate, distance_from_basestation))

#-----------------------------Delete User---------------------------------------------
def deleteUserFromActiveSet(userID):
    del subscriberInfo[userID]#Delete User Info from Dictionary
    if userID in active_user_id:
        active_user_id.remove(userID)#Delete User entry from active call List
    if userID in lowRSLUser:
        lowRSLUser.remove(userID)#Delete User entry from Low RSL call List

#-----------------------------Active User Check---------------------------------------
def checkActiveStatus():#Repeat Every Second, Check if the Active User has completed the call and has Sufficient SINR to sustain the call. Also check if the users who had Low RSL, can make call now
    global successfullCallCompletion
    global numberOfActiveCalls
    global numberOfBlockedCalls
    global numberOfDroppedCalls
    global numberOfBlockedCallsCoverage
    global numberOfCallAttempts
    global numberOfCallAttemptsWithRetry
    global cellRadius
    cellRadius=0
    
    for i in active_user_id:#SINR Check and Call Duration Time Decrement/Check
        pilotRSL=receivedSignalLevel(i)        
	
        #For Users who were in call already, Continue with normal operation of checking if a Call Duration timer has elapsed and if SINR is sufficient to continue the call
        subscriberInfo[i][1]=subscriberInfo[i][1]-1# Decrement Call Duration Timer by one
        if subscriberInfo[i][1]==0:#Check if Call Duration Timer has reached zero
            successfullCallCompletion=successfullCallCompletion+1#Increment Successfull Call Numbers
            deleteUserFromActiveSet(i)#As the Call duration timer has elapsed, remove User from Active List
            numberOfActiveCalls=numberOfActiveCalls-1
        else:
            if SINRCalculation(i,pilotRSL)<REQUIRED_SINR:#Check if Current SINR is less than Required SINR
                if subscriberInfo[i][3]==3:#Check if User has been below the Required SINR for more than 3 seconds
                    numberOfDroppedCalls=numberOfDroppedCalls+1#Drop the call if previous condition is TRUE, Increment Drop call counter
                    deleteUserFromActiveSet(i)#As the Retry counter has elapsed, remove User from Active List
                    numberOfActiveCalls=numberOfActiveCalls-1
                elif subscriberInfo[i][3]=='SINR_Retry_Count':#If its the first time that user has gone below Min_SINR, set the counter to '1'.
                    subscriberInfo[i][3]=1
                else:#If the User is below Required SINR for NOT more tha 3 times, increment the counter
                    subscriberInfo[i][3]=subscriberInfo[i][3]+1
            else:#If User had been below Required SINR before but now has sufficient SINR, reset the "SINR_Retry_Count" counter
                if subscriberInfo[i][3]!='SINR_Retry_Count':
                    subscriberInfo[i][3]='SINR_Retry_Count'

        if i in active_user_id:#Code Block for Maximum Cell Radius Calculation, This condition is to check if user has not been deleted from the Active-List due to low SINR or Call Duration Completion          
            userCellRadius=subscriberInfo[i][0][2]#Get User's Cell Radius
            if userCellRadius>cellRadius:#If User's Cell Radius more than current value in Cell Radius
                cellRadius=userCellRadius#Stores the Cell Radius of the User who is most distant from the Cell


    for i in lowRSLUser:#This code block is for the User who were below Required RSL, and needs to check if he can call now by checking if RSL has improved
        pilotRSL=receivedSignalLevel(i)
        if pilotRSL<MIN_PILOT_RSL:#Check if User still has less RSL than Required
            if subscriberInfo[i][2]==3:#Check if it has already made Three attempts
                deleteUserFromActiveSet(i)#Reject the call and delete User from Active List
                numberOfBlockedCallsCoverage=numberOfBlockedCallsCoverage+1#Increment the "Blocked due to Coverage" counter
                continue
            else:
                subscriberInfo[i][2]=subscriberInfo[i][2]+1#If User has not made 3 attempts, increment the 'Signal_Level_Retry_Count' counter
                numberOfCallAttemptsWithRetry=numberOfCallAttemptsWithRetry+1
        else:#If User has Required RSL Now
            if numberOfActiveCalls<NUMBER_OF_TRAFFIC_CHANNELS:#Check if there is enough capacity to permit the New User
                active_user_id.append(i)#Append the user to Active User List
                lowRSLUser.remove(i)#Remove the user from Low RSL List
                subscriberInfo[i][2]='Signal_Level_Retry_Count'
                numberOfActiveCalls = numberOfActiveCalls + 1#If yes, Increment Number of Active Calls
            else:#If not enough capacity
                numberOfBlockedCalls = numberOfBlockedCalls + 1 #Increment the "Blocked Call Counter" and delete the user from Active List
                deleteUserFromActiveSet(i)#Call can not be made because of capacity issue, remove User from Active List

#-----------------------------------------------New User---------------------------------------------
def newUser():#Repeat Every Second, Identifies the Users who are making call this Second and if there is enough System Capacity available
    global successfullCallCompletion
    global numberOfActiveCalls
    global numberOfBlockedCalls
    global numberOfDroppedCalls
    global numberOfBlockedCallsCoverage
    global numberOfCallAttempts
    global numberOfCallAttemptsWithRetry
    for i in range(NUMBER_OF_USERS):# Choose between 1K/10K Users
        user_id=np.random.randint(1, NUMBER_OF_USERS)#Select any number between 1 and Total Number of Users
        if user_id in active_user_id:#checks if the Randomly generated user is already Active
            continue
        if user_id in lowRSLUser:#checks if the Randomly generated user is already in Low RSL List
            continue
        active_call=np.random.randint(1, (1/PROB_OF_CALLING))#Select any number between 1 and 600, the probablity of user being active is 1/600.
        if user_id%600 == active_call:#Checks if the Randomly generated User is trying to call, uses probability of user being active
            numberOfCallAttempts=numberOfCallAttempts+1
            numberOfCallAttemptsWithRetry=numberOfCallAttemptsWithRetry+1
            subscriberInfo.update({user_id:[userLocation(), userCallDuration(), 'Signal_Level_Retry_Count', 'SINR_Retry_Count']})#Add User Info to the Dictionary
            pilotRSL = receivedSignalLevel(user_id)
            if pilotRSL<MIN_PILOT_RSL:#Check if the User has Required RSL to make the call
                subscriberInfo[user_id][2]=1#If not then count this as one attempt, increment 'Signal_Level_Retry_Count' counter
                lowRSLUser.append(user_id)
            else:
                if numberOfActiveCalls<NUMBER_OF_TRAFFIC_CHANNELS:#Check if there is enough capacity to permit the New User
                    numberOfActiveCalls = numberOfActiveCalls + 1#If yes, Increment Number of Active Calls
                    active_user_id.append(user_id)#Append the user to Active User List
                else:#If not enough capacity
                    numberOfBlockedCalls = numberOfBlockedCalls + 1 #Increment the "Blocked Call Counter" and delete the user from Active List
                    deleteUserFromActiveSet(user_id)#Call can not be made because of capacity issue, remove User from Active List

#----------------------------------Call Duration-------------------------------------------
def userCallDuration():#Random Call Duration based on Exponential Distribution
    while True:
        callDuration = int(np.random.exponential(scale=1.0)*CALL_DURATION)
        if callDuration != 0:#There are instances when it generates Zero as Call Duration, This is to avoid Zero Call Duration
            return(callDuration)
            break

#----------------------------------Shadowing Value Storage Grid-----------------------------------
def shadowingGrid():#Populate the Shadowing Grid (Dictionary) having "key" as Center X and Y Coordinate of the Square, Shadowing Loss as "Value"
    x=-10000+5#Start from left most grid on X-Axis
    for i in range(2000):
        y=10000-5#Start from Upper-most grid on Y-axis
        for j in range(2000):
            grid[(x,y)]=np.random.normal(0,2)#Shadowing calculation based on Gaussian Normal function
            y=y-10#Shift 1 grid downward on each iteration on Y-axis
        x=x+10#Shift 1 grid towards right on each iteration

#----------------------------------Rayleigh Fading Calculation----------------------
def rayleighFadingFun():
    rayleighFading=np.random.rayleigh()#Return a random Rayleigh value
    return (20*math.log10(rayleighFading))#Convert the value to db and return
     

#----------------------------------Propagation Loss---------------------------------------------
def propLoss(distanceKM):#COST231 model implementation, input parameter Distance in KM
    FREQUENCY = 1900 #Frequency in MHz
    BSHEIGHT = 50 #Base station Height in meters
    pathLoss=46.3+33.9*math.log10(FREQUENCY)-13.82*math.log10(BSHEIGHT)+(44.9-6.55*math.log10(BSHEIGHT))*math.log10(distanceKM)
    return pathLoss
#----------------------------------RSL Calculation---------------------------------------------
def receivedSignalLevel(userID):#Calcilates Received Signal Level for the User/Subscriber
    global pilotEIRP
    distanceKM = ((subscriberInfo[userID][0][2])/1000) # Already present in the SubscriberInfo Dictionary, coverted to KM
    receivedLevel = pilotEIRP - propLoss(distanceKM) + rayleighFadingFun() + shadowingLoss(userID)#Pilot RSL Calsulation
    #print('Pilot: ', pilotEIRP, 'Distance: ', distanceKM, 'Pilot RSL: ',receivedLevel) #'Pathloss: ', propLoss(distanceKM),'FastFade: ', rayleighFadingFun(),'ShadowLoass: ',shadowingLoss(userID), 'RSL: ',receivedLevel)
    return receivedLevel

#----------------------------------Shadowing Loss---------------------------------------------
def shadowingLoss(userID):#Returns the Shadowing Loss from the Grid
    xCoordinate = subscriberInfo[userID][0][0]#Extract X-Coordinate of the User
    yCoordinate = subscriberInfo[userID][0][1]#Extract Y-Coordinate of the User
    gridX = (xCoordinate//10)*10+5#Center X-Coordinate of the Grid in which the User falls
    gridY = (yCoordinate//10)*10+5#Center Y-Coordinate of the Grid  in which the User falls
    return (grid[(gridX, gridY)])#Extract and return Shadowing Value from the "grid" Dictionary

#----------------------------------SINR Calculation----------------------------------
def SINRCalculation(userID, pilotRSL):
    global pilotEIRP
    signal_Level= pilotRSL + (MAX_EIRP - pilotEIRP) + PROCESSINGGAIN#Calculates signal level, (MAX_EIRP - pilotEIRP) gives us the difference between Pilot and Traffic Channel EIRP
    if len(active_user_id)<2:
        interference_Level=0#No Interference if only One user in the system
    else:
        interference_Level = pilotRSL + (MAX_EIRP - pilotEIRP) + 10*math.log10(len(active_user_id)-1)#Calculates Interference
    noisePlusInterference=10*math.log10(math.pow(10,interference_Level/10) + math.pow(10,NOISELEVEL/10))#adds Noise and Interference, convert to dB
    signal_to_noise_ratio= signal_Level - noisePlusInterference#Calculates SINR in dB
    #print('Pilo RSL: ', pilotRSL, 'User RSL: ', signal_Level, 'Noise + Interference: ',noisePlusInterference, 'SINR: ',signal_to_noise_ratio)
    return signal_to_noise_ratio

#----------------------------------Optimize Pilot EIRP---------------------------------------------------

def optimizePilotEIRP():# Optimizes the Transmit Power of Pilot channel according to Traffic Channel usage
    global pilotEIRP
    if numberOfActiveCalls>Cd:#IF number of active calls is more than Cd
        if pilotEIRP>MIN_EIRP:#If the current pilot transmit power is more than Minimum Pilot Power
            pilotEIRP=pilotEIRP-Delta_EIRP_Pilot#Decrese pilot power by 0.5 dB
    if numberOfActiveCalls<Ci:#IF number of active calls is less than Ci
        if pilotEIRP<MAX_EIRP:#If the current pilot transmit power is less than Maximum Pilot Power
            pilotEIRP=pilotEIRP+Delta_EIRP_Pilot#Increase pilot power by 0.5 dB
#----------------------------------MAIN---------------------------------------------------
shadowingGrid()#Generate Shadowing Grid
for i in range(1,2*60*60+1):
    checkActiveStatus()#Check Active Calls for Call Duration, SINR
    newUser()#Check for New User
    optimizePilotEIRP()#Check for Pilot Power Optimization based on current channel utilisation

    if i%120==0 and i!=2*60*60:
        print("---------------------------------------------------")
        print("Statistics at ", i/60, " minutes are:")
        print('Number of call attempts not counting retries: ', numberOfCallAttempts)
        print('Number of call attempts including retries: ', numberOfCallAttemptsWithRetry)
        print('Number of dropped calls: ', numberOfDroppedCalls)
        print('Number of blocked calls due to signal strength: ', numberOfBlockedCallsCoverage)
        print('Number of blocked calls due to channel capacity: ', numberOfBlockedCalls)
        print('Number of successfully completed calls: ', successfullCallCompletion)
        print('Number of calls in progress: ', numberOfActiveCalls)
        numberOfFailedCalls=   numberOfDroppedCalls + numberOfBlockedCallsCoverage#Number of failed calls (blocks + drops)
        print('Number of failed calls (blocks + drops): ', numberOfFailedCalls)
        print('Current cell radius(km): ', cellRadius/1000)#Current cell radius (distance between the basestation and the most distant connected user)
        print("Current Pilot EIRP is: ", pilotEIRP)
        
print("---------------------------------------------------")
print("Statistics after 2 hours are:")
print('Number of call attempts not counting retries: ', numberOfCallAttempts)
print('Number of call attempts including retries: ', numberOfCallAttemptsWithRetry)
print('Number of dropped calls: ', numberOfDroppedCalls)
print('Number of blocked calls due to signal strength: ', numberOfBlockedCallsCoverage)
print('Number of blocked calls due to channel capacity: ', numberOfBlockedCalls)
print('Number of successfully completed calls: ', successfullCallCompletion)
print('Number of calls in progress: ', numberOfActiveCalls)
print('Number of failed calls (blocks + drops): ', numberOfFailedCalls)
print('Current cell radius(km): ', cellRadius/1000)
print("Current Pilot EIRP is: ", pilotEIRP)

