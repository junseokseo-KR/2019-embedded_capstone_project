import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from firebase_admin import firestore
import serial
import re
import datetime
from pyfcm import FCMNotification as FCM
from time import sleep

from pyfcm import FCMNotification as FCM

fcm = FCM('AAAAVFTZnik:APA91bGadOo-pamyUCEKftawzJuhsMWQtZ7u-Aq19GKgvM3FPZcz-xTfj80L91Wdzo8TuSCeBEOFgyfAyZnoLudydBdD_njwlXKsdIUFVrZsYuE6NVPO2KxLk_U7hCG0Dp4dJtu2_G7q')

def sendFCM(title, body):
    fcm.notify_single_device(
        registration_id='fiFDMAaL_ZE:APA91bFJi3LAdZg8DpDQdAt9iQDGRphMVZfCvWnEuk-TRFHssRe52RozV8pNeObj9uAP0f6jNt_kOwzucb3PSkUVolA_frOJVYq5aB22GZiP3ZCBQclGrjWaouBNQVVAsg5IeTmMrJ2u',
        message_title=title,
        message_body=body
    )

def getTime():
    now = datetime.datetime.now()
    y = now.year
    M = now.month
    d = now.day
    h = now.hour
    m = now.minute
    s = now.second
    timeMsg = "%s년 %s월 %s일 %s시 %s분 %s초" % (y, M, d, h, m, s)
    return timeMsg

def setBool(ref,boolean):
    boolean = bool(int(''.join(boolean)))
    ref.set(boolean)

def changeVal(ref, val, last):
    val = ref.get()
    if(last!=val):
        ser.write(val)
        print(val)
        last = val

def sendChange(stateType, value):
    msg = '%s = %s' %(stateType,value)
    print(msg.encode())
    ser.write(msg.encode())
    ser.flush()

#firebase 연결
cred = credentials.Certificate("venv/bluebox-dacc6-firebase-adminsdk-ml4xa-0d3b1946c3.json")
firebase_admin.initialize_app(cred,{'databaseURL':'https://bluebox-dacc6.firebaseio.com/'})

#포트 연결
ser = serial.Serial('/COM3',9600)

#레퍼런스 선언
ref=db.reference('/')
myRef=ref.child(u'Lock')
warnRef=ref.child(u'Waring')
sensStateRef=myRef.child(u'isSens')
doorStateRef=myRef.child(u'isDoor')
lockStateRef=myRef.child(u'isLock')
warnStateRef=warnRef.child(u'isWarn')
passwordRef=myRef.child(u'Password')

client = firestore.client()
history_ref = client.collection(u'History')

#레퍼런스 값 변수 선언
lockVal = lockStateRef.get()
doorVal = doorStateRef.get()
sensVal = sensStateRef.get()
warnVal = warnStateRef.get()

lastLockVal = lockVal
lastDoorVal = doorVal
lastSensVal = sensVal
lastWarnVal = warnVal

inserial = False
lastIn = inserial

while True:
    #아두이노로 부터 serial 통신 대기(라즈베리파이<-아두이노)
    while ser.in_waiting:

        #아두이노의 serial을 읽음
        res = ser.readline()

        #serial 통신으로 받은 String 값 가공
        serialVal = res.decode()[:len(res) - 1]
        flag = re.findall(pattern='[a-zA-Z]*', string=serialVal)
        print(serialVal)

        #flag 마다 접하는 레퍼런스 설정
        if('Password' in flag):
            if('ErrorCount' in flag):
                err_cnt = re.findall(pattern='[1-2]', string=serialVal)
                err_cnt = ''.join(err_cnt)
                print('패스워드 에러 ',err_cnt,'회')
            elif('Set'):
                # 숫자(0~9)값인 패스워드를 골라내어 패스워드 레퍼런스 값으로 설정
                password = re.findall(pattern='[0-9]', string=serialVal)
                password = ''.join(password)
                passwordRef.set(u'%s' % password)

        elif('State' in flag):
            #bool의 정수값(0~1)을 골라내어 boolean 변수에 값 설정
            boolean = re.findall(pattern='[0-1]', string=serialVal)
            #각 flag에 맞는 레퍼선스에 boolean 값을 설정
            if('Sens' in flag):
                setBool(sensStateRef, boolean)
            elif('Door' in flag):
                setBool(doorStateRef,boolean)
            elif ('Lock' in flag):
                setBool(lockStateRef, boolean)
                if(''.join(boolean) == '0'):
                    sendFCM("잠금설정","비밀번호가 변경되었습니다.")
                elif(''.join(boolean) == '1'):
                    sendFCM("잠금해제",getTime())
            elif ('Warn' in flag or 'PasswordError' in flag):
                setBool(warnStateRef, boolean)
                body = ''
                if('Warn' in flag):
                    body = '보관함에 큰 충격이 가해졌습니다!'
                elif('PasswordError' in flag):
                    body = '비밀번호 입력을 3회 실패했습니다!'
                sendFCM('경보 발생',body)

    else:
        lockVal = lockStateRef.get()
        warnVal = warnStateRef.get()
        if(lastLockVal != lockVal):
            print("change lockVal")
            lastLockVal = lockVal
            sendChange("lockState",lockVal)
        elif(lastWarnVal != warnVal):
            print("change warnVal")
            lastWarnVal = warnVal
            sendChange("warnState",warnVal)