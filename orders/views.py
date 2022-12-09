from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .forms import Order, Convert
from pymongo import MongoClient
from datetime import datetime
from bson import json_util
import json


# Functions
def check_offers(new_order, bit, fiat, typology):
    '''Funzione che riceve in ingresso un offerta di acquisto/vendita a una certa quantità di bit e moneta fiat, controlla se ci sono delle
    posizioni analoghe aperte e chiude le eventuali posizoni aggiornando i conti degli utenti'''
    # nel caso non ci siano alcuni documenti che rispettano le caratteristiche indicate allora il puntatore del database non punta ad alcun
    # documento e genera un errore. In questo modo se viene generato un errore non faccio nulla altrimenti chiudo le due posizioni di vendita
    # e di acquisto e aggiorno i conti degli utenti
    # imposto le variabili per svolgere le operazioni
    if typology == 'buy':
        type_offer = 'sell'
        bit_old_order = -bit
        bit_new_order = bit
        fiat_old_order = fiat
        fiat_new_order = -fiat
    else:
        type_offer = 'buy'
        bit_old_order = bit
        bit_new_order = -bit
        fiat_old_order = -fiat
        fiat_new_order = fiat
    try:
        # prelevo i dati di eventuali offerte di vendita
        old_order = db.orders.find({'$and': [{'amount_bit': bit}, {'type_offer': type_offer}, {'open_operation': True}]}).sort('date', 1)[0]
        # chiudo le posizioni di acquisto e vendita
        db.users.update_one({'user': old_order.get('user')}, {'$inc': {'bit_balance': bit_old_order, 'fiat_balance': fiat_old_order}})
        db.users.update_one({'user': new_order.get('user')}, {'$inc': {'bit_balance': bit_new_order, 'fiat_balance': fiat_new_order}})
        # aggiorno i bilanci degli utenti
        db.orders.update_one(old_order, {'$set': {'open_operation': False, 'close_operation_date': datetime.now()}})
        db.orders.update_one(new_order, {'$set': {'open_operation': False, 'close_operation_date': datetime.now()}})
    except IndexError:
        pass


# Create your views here.
@csrf_exempt
def pubblic_offert(request):
    '''Funzione che riceve in ingresso una richiesta POST e permette di pubblicare un offerta di acquisto o di vendita solamente se l'utente
    è autenticato.'''
    if request.method != 'POST':
        response = {'Error': 'Request type is wrong.'}
    elif str(request.user) == 'AnonymousUser':
        response = {'Error': 'No one is sing in.'}
    else:
        form = Order(request.POST)
        if form.is_valid():
            typology = form.cleaned_data.get('type_offer')
            bit = form.cleaned_data.get('amount_bit')
            fiat = form.cleaned_data.get('amount_fiat')
            if typology in ['sell', 'buy']:
                # creo l'offerta da pubblicare
                offer = {'user': str(request.user),
                        'type_offer': typology,
                        'amount_bit': bit,
                        'amount_fiat': fiat,
                        'pubbliced_date': datetime.now(),
                        'open_operation': True,
                        'close_operation_date': None}
                # inizializzo le variabili per poter controllare se l'utente può svolgere delle operazioni di vendita/acquisto
                if typology == 'sell':
                    type_balance = 'bit_balance'
                    type_amount_coin = '$amount_bit'
                else:
                    type_balance = 'fiat_balance'
                    type_amount_coin = '$amount_fiat'
                # verifico se l'utente ha abbastanza bitcoin/fiat per poter pubblicare un offerta di vendita/acquisto ottenendo la quantità
                # attuale di bitcoin/fiat dell'utente
                balance_user = db.users.find({'user': str(request.user)}, {type_balance: 1})[0].get(type_balance)
                # ottengo la quantità di bit/fiat utilizzata per pubblicare le varie offerte di vendita/acquisto ancora aperte
                offers = db.orders.aggregate([{'$match': {'user': str(request.user), 'type_offer': typology, 'open_operation': True}},
                                                    {'$group': {'_id': '$user', 'total': {'$sum': type_amount_coin}}}])
                try:
                    sell_offers = list(offers)[0]
                except IndexError:
                    # gestisco l'errore di indice nel caso non ci sono posizioni aperte
                    sell_offers = {'total': 0}
                # se l'utente ha abbastanza bit/fiat pubblico l'offerta
                if typology == 'sell' and balance_user >= sell_offers.get('total')+bit:
                    db.orders.insert_one(offer)
                    response = {'OK': 'Pubbliced.'}
                    # cerco se ci sono delle offerte di acquisto che combaciano all'offerta di vendita
                    check_offers(offer, bit, fiat, typology)
                elif typology == 'buy' and balance_user >= sell_offers.get('total') + fiat:
                    db.orders.insert_one(offer)
                    response = {'OK': 'Pubbliced.'}
                    # cerco se ci sono delle offerte di vendita che combaciano all'offerta di acquisto
                    check_offers(offer, bit, fiat, typology)
                else:
                    if typology == 'buy':
                        response = {'Error': "You haven't much fiat."}
                    else:
                        response = {'Error': "You haven't much bit."}
            else:
                response = {'Error', 'Type order not exist.'}
        else:
            response = {'Error': 'Missing some fields.'}
    return JsonResponse(response, safe=False)


def all_offers(request):
    '''Funzione che ritorna tutti le offerte salvate sul database'''
    if request.method != 'GET':
        response = {'Error': 'Request type is wrong.'}
    elif str(request.user) == 'AnonymousUser':
        response = {'Error': 'No one is sing in.'}
    else:
        # genera un errore nel caso non è salvato alcun documento
        all_offers = db.orders.find().sort([('user', 1), ('type_offer', 1)])
        # converto l'oggetto BSON in JSON
        all_offers = json.loads(json_util.dumps(all_offers))
        response = {'OK': all_offers}
    return JsonResponse(response, safe=False)


def lose_gain(request):
    '''Funzione che ritorna il guadagno/perdita di bit e moneta fiat totale sulle transazioni chiuse per ogni utente'''
    if request.method != 'GET':
        response = {'Error': 'Request type is wrong.'}
    elif str(request.user) == 'AnonymousUser':
        response = {'Error': 'No one is sing in.'}
    else:
        # prendo dal database tutte le informazioni che mi servono
        total_offer_closed = db.orders.aggregate([{'$match': {'open_operation': False}},
                                         {'$group': {
                                             '_id': {'user': '$user', 'type_offer': '$type_offer'},
                                             'bit': {'$sum': '$amount_bit'},
                                             'fiat': {'$sum': '$amount_fiat'}
                                        }}])
        # converto l'oggetto BSON in JSON
        total_offer_closed = json.loads(json_util.dumps(total_offer_closed))
        total_gain_lose_for_user = dict()
        # controllo tutte le informazioni incrementando/decementando in base al tipo di offerta la quantità di bit e fiat
        for offer in total_offer_closed:
            user = offer.get('_id').get('user')
            type_offer = offer.get('_id').get('type_offer')
            bit = offer.get('bit')
            fiat = offer.get('fiat')
            if user in total_gain_lose_for_user:
                if type_offer == 'buy':
                    total_gain_lose_for_user[user]['bit'] += bit
                    total_gain_lose_for_user[user]['fiat'] -= fiat
                else:
                    total_gain_lose_for_user[user]['bit'] -= bit
                    total_gain_lose_for_user[user]['fiat'] += fiat
            else:
                if type_offer == 'buy':
                    total_gain_lose_for_user[user] = dict({'bit': bit, 'fiat': -fiat})
                else:
                    total_gain_lose_for_user[user] = dict({'bit': -bit, 'fiat': fiat})
        response = {'OK': total_gain_lose_for_user}
    return JsonResponse(response, safe=False)


@csrf_exempt
def fiat_bit(request):
    '''Funzione che converte una certa quantià di fiat in bitcoin nel account dell'utente autenticato.'''
    if request.method != 'POST':
        response = {'Error': 'Request type is wrong.'}
    elif str(request.user) == 'AnonymousUser':
        response = {'Error': 'No one is sing in.'}
    else:
        form = Convert(request.POST)
        if form.is_valid():
            # variabile che indica il costo della commmsione da applicare alla conversione
            commission = 2
            user = str(request.user)
            fiat = form.cleaned_data.get('fiat')
            balance = db.users.find({'user': user}, {'fiat_balance': 1})
            # converto l'oggetto BSON in JSON
            balance = json.loads(json_util.dumps(balance))[0]
            if balance.get('fiat_balance') >= fiat:
                db.users.update_one({'user': user}, {'$inc': {'fiat_balance': -fiat, 'bit_balance': fiat-commission}})
                response = {'OK': 'Yuor balances was update.'}
            else:
                response = {'Error': "You don't have enough coins."}
        else:
            response = {'Error': 'Compile both field.'}
    return JsonResponse(response, safe=False)


# creo un oggetto globale per poter comunicare con il database Mongo dove salvo le offerte
client = MongoClient('localhost', 27017)
db = client.exchange_platform
