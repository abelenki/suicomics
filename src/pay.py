#
#   Copyright 2010 Suinova Designs Ltd.
#
# modification on 12/11/2012: remove account constants
#
__author__ = "Ted Wen"
__version__ = "0.1"

import logging
import base64,urllib,cgi,hmac,hashlib
from datetime import datetime
from re import compile
from google.appengine.ext import db
from google.appengine.api import taskqueue
from google.appengine.api import urlfetch
from models import *
import helper
from main import WebRequest
from django.utils import simplejson

PAYMENT_METHODS = ['GC','FC','PP']

#[5,500],[10,1100],[20,2300],[35,4200],[55,6880]
#[4,60],[8,126],[20,315],[40,630],[100,1575]
gPackages = {'sup1':{'id':'Sup1','item':'60 Sudos for 4 GBP','price':4,'quantity':1,'description':'Sudos can be used in all books.','pts':60},
    'sup2':{'id':'Sup2','item':'126 Sudos for 8 GBP','price':8,'quantity':1,'description':'Sudos can be used in all books.','pts':126},
    'sup3':{'id':'Sup3','item':'315 Sudos for 20 GBP','price':20,'quantity':1,'description':'Sudos can be used in all books.','pts':315},
    'sup4':{'id':'Sup4','item':'630 Sudos for 40 GBP','price':40,'quantity':1,'description':'Sudos can be used in all books.','pts':630},
    'sup5':{'id':'Sup5','item':'1575 Sudos for 100 GBP','price':100,'quantity':1,'description':'Sudos can be used in all books.','pts':1575}}

#replace with real ID later, and sandbox with checkout ones:
GC_WHICH = 1    #0=sandbox, 1=real
GC_MERCHANT_IDS = ['','']
GC_MERCHANT_ID = GC_MERCHANT_IDS[GC_WHICH]
GC_MERCHANT_KEYS = ['','']
GC_MERCHANT_KEY = GC_MERCHANT_KEYS[GC_WHICH]
GC_CHECKOUT_SANDBOX_URL = 'https://sandbox.google.com/checkout/api/checkout/v2/merchantCheckout/Merchant/%s'%GC_MERCHANT_ID
GC_CHECKOUT_URL = 'https://checkout.google.com/api/checkout/v2/merchantCheckout/Merchant/%s'%GC_MERCHANT_ID
GC_REQUEST_SANDBOX_URL = 'https://sandbox.google.com/checkout/api/checkout/v2/request/Merchant/%s'%GC_MERCHANT_ID
GC_REQUEST_URL = 'https://checkout.google.com/api/checkout/v2/request/Merchant/%s'%GC_MERCHANT_ID
GC_CHECKOUT_URLS = [GC_CHECKOUT_SANDBOX_URL,GC_CHECKOUT_URL]
GC_REQUEST_URLS = [GC_REQUEST_SANDBOX_URL,GC_REQUEST_URL]

GC_AUTH_HEADER = 'Basic %s'%base64.b64encode('%s:%s' % (GC_MERCHANT_ID,GC_MERCHANT_KEY))
GC_HEADER = {'Content-Type':'application/xml; charset=UTF-8','Accept':'application/xml; charset=UTF-8','Authorization':GC_AUTH_HEADER}

GC_CHECKOUT_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<checkout-shopping-cart xmlns="http://checkout.google.com/schema/2">
<shopping-cart>
<merchant-private-data>%s</merchant-private-data>
<items><item>
<merchant-item-id>%s</merchant-item-id>
<item-name>%s</item-name>
<item-description>%s</item-description>
<unit-price currency="GBP">%d.00</unit-price>
<quantity>%d</quantity>
<digital-content>
<display-disposition>OPTIMISTIC</display-disposition>
<description>
It may take up to several minutes for the Su coins to reach your account.
</description>
</digital-content>
</item></items></shopping-cart>
<checkout-flow-support>
<merchant-checkout-flow-support/>
</checkout-flow-support>
</checkout-shopping-cart>
'''
GC_CONFIRM_XML = '<notification-acknowledgment xmlns="http://checkout.google.com/schema/2" serial-number="%s" />'
GC_CHARGE_SHIP_ORDER='''<?xml version="1.0" encoding="UTF-8"?>
<charge-and-ship-order xmlns="http://checkout.google.com/schema/2" google-order-number="%s">
    <amount currency="%s">%s</amount>
</charge-and-ship-order>
'''

def buypts(web, args=None):
    """ Called when user selected a package from the popup.
        /pay/buypts?pm=GC&pkg=sup1
    """
    web.require_login()
    paymethod,pkgs = web.get_params(['pm','pkg'])
    if paymethod not in PAYMENT_METHODS:
        web.fail('Invalid payment method')
        return
    if pkgs not in gPackages:
        web.fail('Invalid package')
        return
    pkg = gPackages[pkgs]
    if paymethod == 'GC':
        pay_via_google_checkout(web,pkg)
    elif paymethod == 'PP':
        pay_via_paypal(web,pkg)
    elif paymethod == 'FC':
        pay_via_facebook_credit(web,pkg)
    else:
        logging.warning('%s method not supported'%paymethod)
        web.fail('Unsupported payment method')

def pay_via_google_checkout(web,pkg):
    """ Submit a payment request to Google Checkout server. 
        Redirect to the Google payment site if successful.
    """
    logging.info('Authorization: %s'%GC_AUTH_HEADER)
    request_xml = GC_CHECKOUT_XML % (web.user.key().name(),pkg['id'],pkg['item'],pkg['description'],pkg['price'],pkg['quantity'])
    try:
        result = urlfetch.fetch(url=GC_CHECKOUT_URLS[GC_WHICH],payload=request_xml,method=urlfetch.POST,headers=GC_HEADER)
        #logging.info(result.status_code)
        #logging.info(result.content)
        if result.content.find('<redirect-url>')>0:
            n1 = result.content.find('<redirect-url>')
            n2 = result.content.find('</redirect-url>')
            if n2 < n1:
                logging.error('urlfetch returned:%s'%result.content)
                web.fail('Error on request to pay.')    # TODO: should redirect to a error page here
                return
            rurl = result.content[n1+14:n2]
            logging.info('redirecting to %s'%rurl)
            #web.succeed({'url':rurl})
            web.redirect(rurl.replace('&amp;','&'))
        else:
            logging.error('urlfetch returned:%s'%result.content)
            web.fail('Error on request to pay.')
    except Exception,e:
        logging.exception(e)
        web.fail('Error:%s'%e)
    
#PP_ECURL = "https://api-3t.sandbox.paypal.com/nvp"
PP_ECURL = "https://api-3t.paypal.com/nvp"
#PP_URL = "https://www.sandbox.paypal.com/cgi-bin/webscr"
PP_URL = "https://www.paypal.com/cgi-bin/webscr"
#PP_USER = ""
PP_USER = ""
#PP_PWD = ""
PP_PWD = ""
#PP_SIG = ""
PP_SIG = ""
PP_VER = "2.3"
#PayPal API Signature:
#Credential: API Signature
#API Username: 
#API Password: 
#Signature: 

def pay_via_paypal(web,pkg):
    """ Pay via PayPal using Express Checkout, currently using Standard Web method.
        ref: http://code.google.com/p/paypalx-gae-toolkit/
        Test account on PayPal: 
        Seller:  buyer: 
        Test Account:	
        API Username:	
        API Password:	
        Signature:	 
        Merchant Name : 
        Secure Merchant Account ID: 
    """
    logging.debug('pay_via_paypal, user=%s,pkg=%s'%(web.user.key().name(),pkg['id']))
    ukey = web.user.key().name()
    request = {'USER':PP_USER,'PWD':PP_PWD,'SIGNATURE':PP_SIG,'VERSION':PP_VER}
    request['PAYMENTACTION'] = 'Sale'
    request['AMT'] = '%0.2f'%float(gPackages[pkg['id'].lower()]['price'])
    request['CURRENCYCODE'] = 'GBP'
    request['RETURNURL'] = 'https://suicomics.appspot.com/pay/ppapprove?uid=%s&pkg=%s' % (ukey,pkg['id'])
    request['CANCELURL'] = 'https://suicomics.appspot.com/pay/ppcancel'
    request['METHOD'] = 'SetExpressCheckout'
    request['NOSHIPPING'] = '1'
    request['CUSTOM'] = '%s:%s' % (ukey, pkg['id'])   #will return
    request['DESC'] = '%s. %s' % (pkg['item'],pkg['description'])
    request['L_NAME0'] = pkg['item']
    request['L_NUMBER0'] = pkg['id']
    request['L_DESC0'] = pkg['description']
    request['L_AMT0'] = request['AMT']
    request['L_QTY0'] = '1'
    requests = urllib.urlencode(request)
    logging.debug('About to send to PayPal: %s'%requests)
    try:
        result = urlfetch.fetch(url=PP_ECURL,payload=requests,method=urlfetch.POST,headers={'Content-type':'application/x-www-form-urlencoded'})
        if result.content.find('ACK=Success')>=0:
            data = cgi.parse_qs(result.content)
            token = data['TOKEN'][-1]
            web.redirect('%s?cmd=_express-checkout&token=%s' % (PP_URL,token))
        else:
            logging.error('pay.pay_via_paypal(), urlfetch returned: %s'%result.content)
            web.fail('Error contacting PayPal, try later, <a href="/">Go back</a>')
    except Exception,e:
        logging.exception(e)
        web.fail('Error contacting PayPal, try later, <a href="/">Go back</a>')
    
def parse_signed_request(signed_request, secret):
    """ Parse Facebook OAuth 2.0 signed_request.user_id,oauth_token,expires,profile_id(on profile_tab)
    """
    PTN = compile(r'"([^"]+)"\s?:\s?"?([^"}]+)"?')
#    from django.utils import simplejson
    encoded_sig, payload = signed_request.split('.',2)
    sig = base64.b64decode(padtrans(encoded_sig))
    data = simplejson.loads(base64.b64decode(padtrans(payload)))
#    logging.debug('pay.parse_signed_request: datas=%s'%data)
#    data = dict((k,v) for k,v in PTN.findall(datas))
    if data['algorithm'].upper() != 'HMAC-SHA256':
        logging.error('parse_signed_request error, hmac-sha256 expected')
        return None
    expected_sig = hmac.new(secret, msg=payload, digestmod=hashlib.sha256).digest()
    if expected_sig != sig:
        logging.error('parse_signed_request error: bad signature')
        return None
    return data
    
def padtrans(b64s):
    """ Add = padding to multiple of 4.
        And replace - with +, _ with /
    """
    n = 4 - len(b64s) % 4 & 3
    return b64s.replace('-','+').replace('_','/') + '='*n

def pay_via_facebook_credit(web, pkg_secret=None):
    """ This is the routine to handle user payment transactions from facebook.
        /fb/order where pkg is not given there, but inside signed_request
    """
    srequest = web.request.get('signed_request')
#    logging.debug('pay.pay_via_facebook_credit: original signed_request=%s'%srequest)
    signed_request = parse_signed_request(srequest, pkg_secret)
    if not signed_request:
        logging.warning('fb/order: invalid signed_request')
        web.fail('Unauthorized request')
        return
    logging.debug('/fb/order: signed_request = %s'%signed_request)
    payload = signed_request['credits'] #{buyer:2332,order_id:23,order_info:{},receiver:2332}
    order_id = payload['order_id']  #int
    method = web.request.get('method')
    logging.debug('/fb/order: method=%s'%method)
    data = {'method':method}
    if method == 'payments_get_items':
        order_info = payload['order_info']  #{item_id:'sup1',title:'',description:'',price:23,image_url:,product_url:}
        item = simplejson.loads(order_info)
        pkg = item['item_id']   #pkg
        price = gPackages[pkg]['pts']
        if price != item['price']:
            logging.error('Price not correct, may be changed on the client, pkg %s = %s, should be %s' % (pkg,item['price'],price))
            item['price'] = price
        data['content'] = [item]
        taskqueue.add(url='/task/log',params={'usr':'fb_%s'%payload['buyer'],'act':'try to buy %s,#%s'%(pkg,order_id),'dt':str(datetime.utcnow())})
    elif method == 'payments_status_update':
        #payload:{status:'placed',order_id:22,order_details:{},user:{}}
        status = payload['status']
        data['content'] = {'status':'settled','order_id':order_id}
        if status == 'placed':
            logging.debug('/fb/order: status is placed, returning settled')
            order_details = simplejson.loads(payload['order_details'])
            taskqueue.add(url='/task/log',params={'usr':'fb_%s'%order_details['buyer'],'act':'order placed #%s'%order_id,'dt':str(datetime.utcnow())})
        elif status == 'settled':
            #save user purchase transaction here
            logging.debug('/fb/order: settled status received, about to save transaction')
            order_details = simplejson.loads(payload['order_details']) #{order_id:222,buyer:222,app:222,receiver:222,amount:315,update_time:234,time_placed:23,data:'',items:[{}],status:'placed'}
            buyer = order_details['buyer']
            item = order_details['items'][0] #[{item_id:'sup3',title:'',description:'',image_url,product_url,price:315,data:''}]
            data = {'quantity':1,'price':item['price'],'item_id':item['item_id'],'buyer':buyer,'currency':'FC','method':'FC','order_number':order_id}
            logging.debug('/fb/order: save_exchange, data=%s'%data)
            save_exchange('fb_%s' % buyer, datetime.utcnow(), 0, data)
        elif status == 'refunded':
            logging.warning('fb sent refunded')
            data['content']['status'] = status
    datajson = simplejson.dumps(data)
    logging.debug('/fb/order: returning back to fb:%s'%datajson)
    web.response.out.write(datajson)
    
THANKU_PAGE='<html><head><META HTTP-EQUIV="Refresh" CONTENT="3;URL=/"></head><body>Thank you! <a href="/">Go back</a></body></html>'

def ppapprove(web,args=None):
    """ Called by PayPal through RETURNURL set in SetExpressCheckout command.
        Currently payment is done directly, a better way is to return a review page for the user to confirm payment and
        then come back to send DoExpressCheckoutPayment. But the current method is dirty quick.
        The L_NAME0 items are not displayed in the sandbox PayPal continue page, not sure whether it's the same on production site.
    """
    token = web.request.get('token')
    buyerid = web.request.get('PayerID')
    pkg = web.request.get('pkg')
    ukey = web.request.get('uid')
    if pkg == '':
        cs = web.request.get('CUSTOM')
        if cs.find(':') > 0:
            pkg,ukey = cs.split(':')
    logging.debug('pay.ppapprove: token=%s,buyerid=%s,pkg=%s,ukey=%s'%(token,buyerid,pkg,ukey))
    pg = gPackages[pkg.lower()]
    request = {'USER':PP_USER,'PWD':PP_PWD,'SIGNATURE':PP_SIG,'VERSION':PP_VER}
    request['PAYERID'] = buyerid
    request['TOKEN'] = token
    request['PAYMENTACTION'] = 'Sale'
    request['AMT'] = '%0.2f'%float(pg['price'])
    request['CURRENCYCODE'] = 'GBP'
    request['METHOD'] = 'DoExpressCheckoutPayment'
    request['CUSTOM'] = '%s:%s' % (ukey,pkg) # does this return?
    request['DESC'] = '%s. %s' % (pg['item'],pg['description'])
    request['L_NAME0'] = pg['item']
    request['L_NUMBER0'] = pg['id']
    request['L_DESC0'] = pg['description']
    request['L_AMT0'] = request['AMT']
    request['L_QTY0'] = '1'
    requests = urllib.urlencode(request)
    logging.debug('About to send to PayPal: %s'%requests)
    try:
        result = urlfetch.fetch(url=PP_ECURL,payload=requests,method=urlfetch.POST,headers={'Content-type':'application/x-www-form-urlencoded'})
        if result.content.find('ACK=Success')>=0:
            data = cgi.parse_qs(result.content)
            #token = data['TOKEN'][-1]
            payment_status = data['PAYMENTSTATUS'][0]
            if payment_status == 'Completed':
                data2 = {'method':'PP','quantity':'1','item_id':pkg,'buyer':buyerid}
                data2['order_number'] = data['TRANSACTIONID'][0]
                data2['price'] = data['AMT'][0]
                data2['currency'] = data['CURRENCYCODE'][0]
                if 'SETTLEAMT' in data:
                    logging.debug('settlement: %s'%data['SETTLEAMT'][0])
                fee = float(data['FEEAMT'][0])
                tstamp = datetime_from_timestampz(data['ORDERTIME'][0])
                buyer = helper.get_user_by_key(ukey,False)
                if buyer is None:
                    logging.warning('Buyer %s is not user!'%ukey)
                    helper.send_email('Suinova test payment failure notification','Buyer %s not found'%ukey)
                    web.response.out.write('Thank you!')
                    return
                try:
                    save_exchange(buyer,tstamp,fee,data2)
                except Exception:
                    pass
                web.response.out.write(THANKU_PAGE)
            else:
                logging.warning('ppapprove result from DoExpressCheckoutPayment, payment status is %s'%payment_status)
                logging.info(result.content)
                web.response.out.write('Not completed')
        else:
            logging.error('ppapprove send DoExpressCheckoutPayment returned: %s'%result.content)
            web.fail('Error contacting PayPal, try later, <a href="/">Go back</a>')
    except Exception,e:
        logging.exception(e)
        web.fail('Error contacting PayPal, try later, <a href="/">Go back</a>')
    
def ppcancel(web,args=None):
    """ Called by PayPal through CANCELURL.
    """
    web.fail('Error contacting PayPal, try later, <a href="/">Go back</a>')
    
#deprecated: old using IPN
def paypalipn(web,args=None):
    """ Listener to PayPal notification. """
    my_email = web.request.get('receiver_email')    #check this to prevent fraud
    if my_email != 'suinov_1261417753_biz@gmail.com':
        logging.warning('PayPal IPN wrong receiver_email:%s'%my_email)
        web.response.out.write('Ok')
        return
    status = web.request.get('payment_status')
    if status != 'Completed':
        logging.debug('PayPal IPN status not Completed')
        web.response.out.write('Ok')
        return
    parameters = '&'.join(['cmd=_notify-validate']+['%s=%s'%(k,web.request.get(k)) for k in web.request.arguments()])
    logging.debug('paypalipn, parameters=%s'%parameters)
    try:
        result = urlfetch.fetch(url=PP_URL,payload=parameters,method=urlfetch.POST,headers={'Content-type':'application/x-www-form-urlencoded'})
        if result.content == 'VERIFIED':
            data = {}
            data['orderef'] = web.request.get('txn_id')
            data['buyer'] = web.request.get('payer_id')
            invoice_id = web.request.get('invoice')
            data['currency'] = web.request.get('mc_currency')
            data['price'] = web.request.get('mc_gross')
            data['item_id'] = web.request.get('custom')
            data['quantity'] = web.request.get('quantity')
            fee = web.request.get('mc_fee')
            email = web.request.get('payer_email')
            identifier = web.request.get('payer_id')
            #check whether this transaction is saved in SuiExchange, if not save
            try:
                save_exchange(buyer,tstamp,fee,data)
            except Exception:
                pass
            web.response.out.write('Ok')
    except Exception,e:
        logging.exception(e)
        web.error(500)
        
    
def extract_text_in_tag(xmls, tag):
    ptn = compile(r'<%s[\w ="_]*>([^<]*)</%s>'%(tag,tag))
    return ptn.findall(xmls)
    
SPTN = compile(r'serial-number="([\w\-]+)"')

def get_google_notification_data(xmls):
    """ Extract useful values from notification document. It is assumed only one item is purchased.
        @return {'order_number':'','item_id':'Sup1','quantity':1,'price':1.0}
    """
    #logging.info('pay.get_google_notification_data, xml=%s'%xmls)
    sptn = SPTN.findall(xmls)
    if len(sptn) < 0:
        logging.error('Google Checkout notification bad (no order_number):%s'%xmls)
        return None
    rs = {'serial-number':sptn[0]}
    order_numbers = extract_text_in_tag(xmls, 'google-order-number')
    if len(order_numbers) <= 0:
        logging.error('Google Checkout notification bad (no order_number):%s'%xmls)
        return None
    rs['order_number'] = order_numbers[0]
    items = extract_text_in_tag(xmls, 'merchant-item-id')
    if len(items) <= 0:
        logging.error('No merchant-item-id in Google Checkout notification:%s'%xmls)
        return None
    rs['item_id'] = items[0]
    qtys = extract_text_in_tag(xmls, 'quantity')
    if len(qtys) <= 0:
        logging.error('No quantity in Google Checkout notification:%s'%xmls)
        return None
    rs['quantity'] = int(qtys[0])
    uprice = extract_text_in_tag(xmls, 'unit-price')
    if len(uprice) <= 0:
        logging.error('No unit-price in Google Checkout notification:%s'%xmls)
        return None
    rs['price'] = uprice[0]
    rs['buyer'] = extract_text_in_tag(xmls, 'buyer-id')[0]
    rs['timestamp'] = extract_text_in_tag(xmls, 'timestamp')[0]  #2007-03-19T15:06:25.051Z
    tptn = compile(r'<order-total currency="(\w+)">([\d.]+)</order-total>')
    tt = tptn.findall(xmls)
    if len(tt) > 0:
        rs['currency'] = tt[0][0]
        rs['total'] = tt[0][1]
    ob = extract_text_in_tag(xmls, 'merchant-private-data')
    if len(ob) > 0:
        rs['original_buyer'] = ob[0]
    return rs
    
def make_timestamps():
    return datetime.utcnow().isoformat()    #'2010-09-24T15:05:07.843000'
    
def datetime_from_timestampz(ts):
    """ Convert ISO-format datetime with Z to datetime object. this is for Python 2.5 
        @param ts: 2010-01-01T01:01:01.123Z or 2010-01-01T01:01:01Z
    """
    dt = ts.strip('Z').split('.')
    d1 = datetime.strptime(dt[0],'%Y-%m-%dT%H:%M:%S')
    if len(dt)>1:
        ms = int(dt[1].ljust(6,'0')[:6])
        return d1.replace(microsecond=ms)
    else:
        return d1
    
def gcnotify(web,args=None):
    """ Google Checkout Notification listener. Called by Google Checkout Server.
    """
    auth = web.request.headers['Authorization']
    logging.info('in pay.gcnotify:%s'%auth)
    if auth != GC_AUTH_HEADER:
        logging.warning('Auth header incorrect')
        web.response.set_status(401)
        return
    msg = web.request.body
    if msg.find('new-order-notification') > 0:
        # actually, we need do nothing on this notification, only a notice that a new order is on the way
        logging.info('Got new-order-notification')
        #extract buyer and item info
        data = get_google_notification_data(msg)
        if data is None:
            web.response.set_status(400)    #200 by default
        web.response.out.write(GC_CONFIRM_XML % data['serial-number'])
        #order_number = extract_text_in_tag(msg, 'google-order-number')[0]
        #items = extract_text_in_tag(msg, 'merchant-item-id')
        #itemnames = extract_text_in_tag(msg, 'item-name')
        #qtys = extract_text_in_tag(msg, 'quantity')
        #uprice = extract_text_in_tag(msg, 'unit-price')
        #only one item per purchase possible
        #buyer = extract_text_in_tag(msg, 'buyer-id')[0]
        #state = extract_text_in_tag(msg, 'financial-order-state')[0]  #REVIEWING,CHARGING
    elif msg.find('authorization-amount-notification') > 0:
        # here is when the user actually paid and we can charge her now
        logging.info('Got authorization-amount-notification')
        data = get_google_notification_data(msg)
        if data is None:
            web.response.set_status(400)
        web.response.out.write(GC_CONFIRM_XML % data['serial-number'])
        #send_charge_command(msg)
        logging.debug('gcnotify queue task /pay/gccharge with %s'%data)
        taskqueue.add(url='/pay/gccharge',params=data)
        

def gccharge(web, args=None):
    """ Internal taskqueue to send a charge-and-ship request to Google Checkout server.
        If a charge-amount-notification is returned back, save the data into database now.
    """
    order_number,total,currency = web.get_params(['order_number','total','currency'])
    if order_number == '':
        logging.error('No order_number in parameter')
        web.succeed()
        return
    #send back charge request now
    request_xml = GC_CHARGE_SHIP_ORDER % (order_number,currency,total)
    logging.debug('gccharge send to goodle checkout: %s'%request_xml)
    try:
        result = urlfetch.fetch(url=GC_REQUEST_URLS[GC_WHICH],payload=request_xml,method=urlfetch.POST,headers=GC_HEADER);
    except Exception,e:
        logging.exception(e)
        web.error(500)  #will cause resend to google checkout
    try:
        if result.content.find('<charge-amount-notification') > 0:
            #charged, so save in ds
            data = get_google_notification_data(result.content)
            if 'original_buyer' not in data:
                ers = 'merchange-private-data not available in charge-amount-notification'
                logging.error(ers)
                helper.send_email('Suinova test payment failure notification',ers)
                web.succeed()    #return 200 not to resend to Google Checkout
                return
            buyer_id = data['original_buyer']
            buyer = helper.get_user_by_key(buyer_id,False)    #'gg_%s' % data['buyer'])
            if buyer is None:
                logging.warning('Buyer %s is not user!'%buyer_id)
                helper.send_email('Suinova test payment failure notification','Buyer %s not found'%buyer_id)
                web.succeed()   #return 200 not to resend to Google Checkout
                return
            gcfee = extract_text_in_tag(result.content,'total')
            if len(gcfee)>0:
                try:
                    fee = float(gcfee[0])
                except TypeError,e:
                    logging.error('float(%s) error:%s'%(gcfee[0],e))
                    fee = 0
            else:
                fee = 0
            pkg_id = data['item_id']
            tstamp = datetime_from_timestampz(data['timestamp'])
            
            data['method'] = 'GC'
            try:
                save_exchange(buyer,tstamp,fee,data)
            except Exception,e:
                pass
            web.succeed()
        else:
            logging.error('No <charge-amount-notification> received, but %s'%result.content)
            #
    except Exception,e:
        logging.exception(e)
        helper.send_email('Suinova test payment failure notification',str(e))
        web.succeed()
        
def save_exchange(buyer,tstamp,fee,data):
    """ Save a new SuiExchange entity if not saved yet, key_name is method_order_number.
        @param data : {'item_id':'sup1','quantity':1,'price':10,'order_number':'2343-3422','currency':'GBP','method':'GC'}
        @exception : db error
    """
    m = data['method']
    on = data['order_number']
    keyname = '%s_%s' % (m, on)
    exe = SuiExchange.get_by_key_name(keyname)
    if isinstance(buyer,basestring):
        ukey = buyer
        buyer = helper.query_user_by_key(ukey)
    else:
        ukey = buyer.key().name() 
    if exe is None:
        exe = SuiExchange(key_name=keyname,user=ukey,xtime=tstamp)
        q = int(data['quantity'])
        pkg = data['item_id']
        exe.points = q * gPackages[pkg.lower()]['pts']
        exe.quantity = q
        exe.price = float(data['price'])
        exe.orderef = '%s'%on
        exe.currency = data['currency']
        exe.method = data['method']
        exe.buyerid = '%s'%data['buyer']
        exe.package = pkg
        exe.fee = 1.0 * (fee or 1)
        taskqueue.add(url='/task/log',params={'usr':ukey,'act':'bought %s,%s+%s'%(pkg,buyer.points,exe.points),'dt':str(datetime.utcnow())})
        try:
            exe.put()
            buyer.points += exe.points
            buyer.save()
            logging.debug('SuiExchange saved, %s, %s' % (m, on))
            taskqueue.add(url='/task/dau',params={'usr':buyer.key().name(),'act':'pay','par':pkg,'qty':str(q)})
        except Exception,e:
            logging.exception('SuiExchange.put() failed:%s'%e)
            helper.send_email('Suinova test payment failure notification',str(e))
            raise
    else:
        logging.warning('SuiExchange existed for %s' % keyname)
    return True
    