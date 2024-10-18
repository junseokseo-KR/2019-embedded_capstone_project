import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from firebase_admin import firestore
import serial
import re
import datetime
from pyfcm import FCMNotification as FCM

fcm = FCM('')

def sendFCM(title, body):
    fcm.notify_single_device(
        registration_id='',
        message_title=title,
        message_body=body
    )

def getDateTime():
    now = datetime.datetime.now()
    y = now.year
    M = now.month
    d = now.day
    h = now.hour
    m = now.minute
    s = now.second
    dateTimeMsg = "%s년 %s월 %s일 %s시 %s분 %s초" % (y, M, d, h, m, s)
    return dateTimeMsg

def getDate():
    now = datetime.datetime.now()
    y = now.year
    M = now.month
    d = now.day
    dateMsg = "%s년 %s월 %s일" % (y, M, d)
    return dateMsg

def getTime():
    now = datetime.datetime.now()
    h = now.hour
    m = now.minute
    s = now.second
    timeMsg = "%s시 %s분 %s초" % (h, m, s)
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

def addHistory(ref, type):
    stamp = datetime.datetime.now().timestamp()
    doc = ref.document('%s [%s]'%(stamp, type))
    doc.set({
        u'Type': u'%s' % type,
        u'Date': u'%s' % getDate(),
        u'Time': u'%s' % getTime(),
    })


#firebase 연결
cred = credentials.Certificate("venv/bluebox-dacc6-firebase-adminsdk-ml4xa-0d3b1946c3.json")
# cred = credentials.Certificate("/home/pi/blackbox/2019-embedded_capstone_project/venv/bluebox-dacc6-firebase-adminsdk-ml4xa-0d3b1946c3.json")
firebase_admin.initialize_app(cred,{'databaseURL':'https://bluebox-dacc6.firebaseio.com/'})

#포트 연결
ser = serial.Serial('/COM3',9600)
# ser = serial.Serial('/dev/ttyACM0',9600)

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
                lockVal = bool(int(''.join(boolean)))
                lastLockVal = bool(int(''.join(boolean)))
                setBool(lockStateRef, boolean)
                if(''.join(boolean) == '0'):
                    sendFCM("잠금설정","비밀번호가 변경되었습니다.")
                    addHistory(history_ref, '잠금설정')
                elif(''.join(boolean) == '1'):
                    sendFCM("잠금해제", getDateTime())
                    addHistory(history_ref, '잠금해제')
            elif ('Warn' in flag or 'PasswordError' in flag):
                setBool(warnStateRef, boolean)
                body = ''
                boolStr = ''.join(boolean)
                if('Warn' in flag):
                    if(boolStr=='1'):
                        body = '보관함에 큰 충격이 가해졌습니다!'
                        addHistory(history_ref, '충격 감지')
                elif('PasswordError' in flag):
                    if (boolStr == '1'):
                        body = '비밀번호 입력을 3회 실패했습니다!'
                        addHistory(history_ref,'비밀번호 3회 실패')
                sendFCM('경보 발생',body)
        elif('Init' in flag):
            sendFCM("서버 접속 성공","초기화 완료")
            setBool(sensStateRef, '0')
            setBool(doorStateRef, '0')
            setBool(lockStateRef, '0')
            setBool(warnStateRef, '0 ')

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
