import requests
from django.shortcuts import render
from paytmchecksum import PaytmChecksum

from .models import Product, Contact, Orders,OrderUpdate
from math import ceil
# import the logging library
import logging
import json
from django.views.decorators.csrf import csrf_exempt
from PayTm import Checksum
# Get an instance of a logger
logger = logging.getLogger(__name__)
# Create your views here.
from django.http import HttpResponse
MERCHANT_KEY = 'S8qbumhqZSGo%Px#'

def index(request):

    allprods = []
    catprods = Product.objects.values('category', 'id')
    cats = {item['category'] for item in catprods}
    for cat in cats:
        prod = Product.objects.filter(category=cat)
        n = len(prod)
        nslides = n // 4 + ceil((n / 4) - (n // 4))
        allprods.append([prod, range(1, nslides), nslides])

    params = {'allprods': allprods}
    return render(request, 'shop/index.html', params)


def searchMatch(query, item):
    if query in item.desc.lower() or query in item.product_name.lower() or query in item.category.lower():
        return True
    else:
        return False


def search(request):
    query = request.GET.get('search')
    allprods = []
    catprods = Product.objects.values('category', 'id')
    cats = {item['category'] for item in catprods}
    for cat in cats:
        prodtemp = Product.objects.filter(category=cat)
        prod = [item for item in prodtemp if searchMatch(query, item)]
        n = len(prod)
        nslides = n // 4 + ceil((n / 4) - (n // 4))
        if(len(prod)!=0):
            allprods.append([prod, range(1, nslides), nslides])

    params = {'allprods': allprods, 'msg': ""}
    if len(allprods) == 0 or len(query) < 4:
        params = {'msg': "Please enter relevent search"}
    return render(request, 'shop/search.html', params)




def about(request):
    return render(request, 'shop/about.html')

def contact(request):
    if request.method == "POST":
        name = request.POST.get('name', '')
        email = request.POST.get('email', '')
        phone = request.POST.get('phone', '')
        desc = request.POST.get('desc', '')
        contact = Contact(name=name, email=email, phone=phone, desc=desc)
        contact.save()
    return render(request, 'shop/contact.html')

def tracker(request):
    if request.method=="POST":
        orderId = request.POST.get('orderId', '')
        email = request.POST.get('email', '')
        try:
            order = Orders.objects.filter(order_id=orderId,email=email)
            if len(order)>0:
                update=OrderUpdate.objects.filter(order_id=orderId)
                updates = []
                for item in update:
                    updates.append({'text':item.update_desc,'time':item.timestamp})
                    response = json.dumps({"status":"success", "updates": updates, "itemsJson":order[0].items_json}, default=str)
                return HttpResponse(response)
            else:
                return HttpResponse('{"status":"noitem"}')
        except Exception as e:
            return HttpResponse('{"status":"error"}')

    return render(request, 'shop/tracker.html')


def productView(request, myid):
    # Fetch the product using the id
    product = Product.objects.filter(id=myid)


    return render(request, 'shop/prodView.html', {'product':product[0]})

def checkout(request):
    if request.method=="POST":
        items_json = request.POST.get('itemsJson', '')
        name = request.POST.get('name', '')
        amount = request.POST.get('amount', '')
        email = request.POST.get('email', '')
        address = request.POST.get('address1', '') + " " + request.POST.get('address2', '')
        city = request.POST.get('city', '')
        state = request.POST.get('state', '')
        zip_code = request.POST.get('zip_code', '')
        phone = request.POST.get('phone', '')
        order = Orders(items_json=items_json, name=name, email=email, address=address, city=city,
                       state=state, zip_code=zip_code, phone=phone, amount=amount)
        order.save()
        update = OrderUpdate(order_id=order.order_id, update_desc="The order has been placed")
        update.save()
        thank = True
        id = order.order_id
        # return render(request, 'shop/checkout.html', {'thank':thank, 'id': id})
        # # Request paytm to transfer the amount to your account after payment by user
        param_dict = {
        
                'MID': 'xLTIDt18542930146895',
                'ORDER_ID': str(order.order_id),
                'TXN_AMOUNT': "1",
                'CUST_ID': email,
                'INDUSTRY_TYPE_ID': 'Retail',
                'WEBSITE': 'DEFAULT',
                'CHANNEL_ID': 'WEB',
                'CALLBACK_URL':'http://127.0.0.1:8000/shop/handlerequest/',
        
        }
        param_dict['CHECKSUMHASH'] = Checksum.generate_checksum(param_dict, MERCHANT_KEY)
        return render(request, 'shop/paytm.html', {'param_dict': param_dict})
        #paytmParams = dict()

        # paytmParams["body"] = {
        #     "requestType": "Payment",
        #     "mid": "xLTIDt18542930146895",
        #     "websiteName": "YOUR_WEBSITE_NAME",
        #     "orderId": "1632482687",
        #     "callbackUrl": 'http://127.0.0.1:8000/shop/handlerequest/',
        #     "txnAmount": {
        #         "value": "1.00",
        #         "currency": "INR",
        #     },
        #     "userInfo": {
        #         "custId": "CUST_001",
        #     },
        # }

        # # Generate checksum by parameters we have in body
        # # Find your Merchant Key in your Paytm Dashboard at https://dashboard.paytm.com/next/apikeys
        # checksum = PaytmChecksum.generateSignature(json.dumps(paytmParams["body"]), MERCHANT_KEY)

        # paytmParams["head"] = {
        #     "signature": checksum
        # }

        # post_data = json.dumps(paytmParams)

        # # for Staging
        # #url = "https://securegw-stage.paytm.in/theia/api/v1/initiateTransaction?mid=KVwGlH78656636401912&orderId=98765"

        # # for Production
        # url = "https://securegw.paytm.in/theia/api/v1/initiateTransaction?mid=xLTIDt18542930146895&orderId=1632482687"
        # response = requests.post(url, data=post_data, headers={"Content-type": "application/json"}).json()
        # print(response)
        # return render(request, 'shop/paytm.html', {'param_dict': response})

    return render(request, 'shop/checkout.html')



@csrf_exempt
def handlerequest(request):
    # paytm will send you post request here
    form = request.POST
    response_dict = {}
    for i in form.keys():
        response_dict[i] = form[i]
        if i == 'CHECKSUMHASH':
            checksum = form[i]

    verify = Checksum.verify_checksum(response_dict, MERCHANT_KEY, checksum)
    if verify:
        if response_dict['RESPCODE'] == '01':
            print('order successful')
        else:
            print(response_dict)
            print('order was not successful because' + response_dict['RESPMSG'])
    return render(request, 'shop/paymentstatus.html', {'response': response_dict})

