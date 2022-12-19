from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .forms import Order, Convert, OrderId
from pymongo import MongoClient
from datetime import datetime
from bson import json_util
import json
from bson.objectid import ObjectId


# Functions
def check_offers(new_order):
    '''Funzione che riceve in ingresso un offerta di acquisto/vendita a una certa quantità di bit e moneta fiat, controlla se ci sono delle
    posizioni aperte, chiude le eventuali corrispondenti posizoni aggiornando i conti degli utenti e aggiungengo ai documenti il guadagno
    o perdita subita.'''
    # nel caso non ci siano alcuni documenti che rispettano le caratteristiche indicate allora il puntatore del database non punta ad alcun
    # documento e genera un errore. In questo modo se viene generato un errore non faccio nulla altrimenti chiudo le due posizioni di vendita
    # e di acquisto e aggiorno i conti degli utenti
    # imposto le variabili per svolgere le operazioni:
    # - quantità di bit inerente al ultima offerta pubblicata
    bit = new_order.get('amount_bit').get('available')
    # - quantità di fiat inerente al ultima offerta pubblicata
    fiat = new_order.get('amount_fiat')
    # - tipologia di offerta pubblicata
    typology = new_order.get('type_offer')
    # - nome dell'utente
    user = new_order.get('user')
    if typology == 'buy':
        query = {'$and': [{'amount_fiat': {'$lte': fiat}}, {'type_offer': 'sell'}, {'open_operation': True}]}
        total_orders = db.orders.find(query).sort('amount_fiat', 1)
        # imposto le variabili per aggiornare la quantità di fiat e bit dei account degli utenti a cui combaciano le offerte
        account_user_increment_bit = user
        if db.orders.count_documents(query) > 0:
            account_user_increment_fiat = total_orders[0].get('user')
    else:
        query = {'$and': [{'amount_fiat': {'$gte': fiat}}, {'type_offer': 'buy'}, {'open_operation': True}]}
        total_orders = db.orders.find(query).sort('amount_fiat', -1)
        # imposto le variabili per aggiornare la quantità di fiat e bit dei account degli utenti a cui combaciano le offerte
        account_user_increment_fiat = user
        if db.orders.count_documents(query) > 0:
            account_user_increment_bit = total_orders[0].get('user')
    # controllo tutte le posizioni di vendita/acquisto e chiudo quelle che combaciano con l'offerta appena pubblicata
    for order in total_orders:
        # inizializzo le variabili che mi permettono di memorizzare nel documento la quantità guadagnata/persa di bit e fiat
        # se è un ordine di acquisto allora guadagno bit e perdo moneta fiat
        if typology == 'buy':
            old_order_gain_bit = -bit
            old_order_gain_fiat = bit * order.get('amount_fiat')
            new_order_gain_bit = bit
            new_order_gain_fiat = -bit * order.get('amount_fiat')
        # se è un ordine di vendita allora perdo bit e guadagno moneta fiat
        else:
            old_order_gain_bit = bit
            old_order_gain_fiat = -bit * order.get('amount_fiat')
            new_order_gain_bit = -bit
            new_order_gain_fiat = bit * order.get('amount_fiat')
        if order.get('amount_bit').get('available') == bit:
            # aggiorno gli ordini: chiudendoli o decrementando la quantità pubblicata
            db.orders.update_one(order, {'$set': {'open_operation': False, 'close_operation_date': datetime.now()},
                                         '$inc': {'amount_bit.available': -bit, 'amount_bit.no_available': bit,
                                                  'gain_bit': old_order_gain_bit, 'gain_fiat': old_order_gain_fiat}})
            db.orders.update_one(new_order, {'$set': {'open_operation': False, 'close_operation_date': datetime.now()},
                                             '$inc': {'amount_bit.available': -bit, 'amount_bit.no_available': bit,
                                                      'gain_bit': new_order_gain_bit, 'gain_fiat': new_order_gain_fiat}})
            # aggirno gli account degli utenti incrementando/decrementando la quantità di fiat/bit
            db.users.update_one({'user': account_user_increment_bit}, {'$inc': {'bit_balance': bit,
                                                                                'fiat_balance': -order.get('amount_fiat')*bit}})
            db.users.update_one({'user': account_user_increment_fiat}, {'$inc': {'bit_balance': -bit,
                                                                                 'fiat_balance': order.get('amount_fiat')*bit}})
            break
        elif order.get('amount_bit').get('available') > bit:
            # aggiorno gli ordini: chiudendoli o decrementando la quantità pubblicata
            db.orders.update_one(order, {'$inc': {'amount_bit.available': -bit, 'amount_bit.no_available': bit,
                                                  'gain_bit': old_order_gain_bit, 'gain_fiat': old_order_gain_fiat}})
            db.orders.update_one(new_order, {'$set': {'open_operation': False, 'close_operation_date': datetime.now()},
                                             '$inc': {'amount_bit.available': -bit, 'amount_bit.no_available': bit,
                                                      'gain_bit': new_order_gain_bit, 'gain_fiat': new_order_gain_fiat}})
            # aggirno gli account degli utenti incrementando/decrementando la quantità di fiat/bit
            db.users.update_one({'user': account_user_increment_bit}, {'$inc': {'bit_balance': bit,
                                                                                'fiat_balance': -order.get('amount_fiat')*bit}})
            db.users.update_one({'user': account_user_increment_fiat}, {'$inc': {'bit_balance': -bit,
                                                                                 'fiat_balance': order.get('amount_fiat')*bit}})
            break
        elif order.get('amount_bit').get('available') < bit:
            # modifico le variabili percedentemente create
            if typology == 'buy':
                old_order_gain_bit = -order.get('amount_bit').get('available')
                old_order_gain_fiat = order.get('amount_bit').get('available') * order.get('amount_fiat')
                new_order_gain_bit = order.get('amount_bit').get('available')
                new_order_gain_fiat = -order.get('amount_bit').get('available') * order.get('amount_fiat')
            else:
                old_order_gain_bit = order.get('amount_bit').get('available')
                old_order_gain_fiat = -order.get('amount_bit').get('available') * order.get('amount_fiat')
                new_order_gain_bit = -order.get('amount_bit').get('available')
                new_order_gain_fiat = order.get('amount_bit').get('available') * order.get('amount_fiat')
            # aggiorno gli ordini: chiudendoli o decrementando la quantità pubblicata
            db.orders.update_one(order, {'$set': {'open_operation': False, 'close_operation_date': datetime.now()},
                                         '$inc': {'amount_bit.available': -order.get('amount_bit').get('available'),
                                                  'amount_bit.no_available': order.get('amount_bit').get('available'),
                                                  'gain_bit': old_order_gain_bit, 'gain_fiat': old_order_gain_fiat}})
            db.orders.update_one(new_order, {'$inc': {'amount_bit.available': -order.get('amount_bit').get('available'),
                                                      'amount_bit.no_available': order.get('amount_bit').get('available'),
                                                      'gain_bit': new_order_gain_bit, 'gain_fiat': new_order_gain_fiat}})
            # aggirno gli account degli utenti incrementando/decrementando la quantità di fiat/bit
            db.users.update_one({'user': account_user_increment_bit}, {'$inc': {'bit_balance': order.get('amount_bit').get('available'),
                                                                                'fiat_balance': -order.get('amount_fiat')*order.get('amount_bit').get('available')}})
            db.users.update_one({'user': account_user_increment_fiat}, {'$inc': {'bit_balance': -order.get('amount_bit').get('available'),
                                                                                 'fiat_balance': order.get('amount_fiat')*order.get('amount_bit').get('available')}})
            # aggiorno la quantità di bit che è stata acquistata/venduta in modo che al ciclo successivo i dati sono corretti
            bit -= order.get('amount_bit').get('available')
            new_order['amount_bit']['available'] -= order.get('amount_bit').get('available')
            new_order['amount_bit']['no_available'] += order.get('amount_bit').get('available')


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
            # istanzio le variabili che mi servono successivamente
            typology = form.cleaned_data.get('type_offer')
            bit = form.cleaned_data.get('amount_bit')
            fiat = form.cleaned_data.get('amount_fiat')
            if typology in ['sell', 'buy']:
                # creo l'offerta da pubblicare
                offer = {'user': str(request.user),
                        'type_offer': typology,
                        'amount_bit': {'available': bit, 'no_available': 0},
                        'amount_fiat': fiat,
                        'pubbliced_date': datetime.now(),
                        'open_operation': True,
                        'close_operation_date': None}
                # verifico se l'utente ha abbastanza bitcoin/fiat per poter pubblicare un offerta di vendita/acquisto ottenendo la quantità
                # attuale di bitcoin/fiat dell'utente
                # inizializzo una variabile dove memorizzo la quantità spesa dall'utente per pubblicare le offerte non ancora chiuse
                cost_operation_open = 0
                # ottengo la quantità di fiat utilizzata per pubblicare le varie offerte di acquisto ancora aperte
                if typology == 'buy':
                    balance_user = db.users.find({'user': str(request.user)}, {'fiat_balance': 1})[0].get('fiat_balance')
                    offers = db.orders.find({'user': str(request.user), 'type_offer': typology, 'open_operation': True},
                                            {'amount_fiat': 1, 'amount_bit.available': 1})
                    for off in offers:
                        cost_operation_open += off.get('amount_fiat') * off.get('amount_bit').get('available')
                # ottengo la quantità di bit utilizzata per pubblicare le varie offerte di acquisto ancora aperte
                else:
                    balance_user = db.users.find({'user': str(request.user)}, {'bit_balance': 1})[0].get('bit_balance')
                    results = db.orders.aggregate([{'$match': {'user': str(request.user), 'type_offer': typology, 'open_operation': True}},
                                                    {'$group': {'_id': '$user', 'total': {'$sum': '$amount_bit.available'}}}])
                    try:
                        cost_operation_open = list(results)[0].get('total')
                    except IndexError:
                        # gestisco l'errore di indice nel caso non ci sono posizioni aperte
                        cost_operation_open = 0
                # se l'utente ha abbastanza bit/fiat pubblico l'offerta
                if typology == 'sell' and balance_user >= cost_operation_open + bit:
                    db.orders.insert_one(offer)
                    response = {'OK': 'Pubbliced.'}
                    # cerco se ci sono delle offerte di acquisto che combaciano all'offerta di vendita
                    check_offers(offer)
                elif typology == 'buy' and balance_user >= cost_operation_open + (fiat * bit):
                    db.orders.insert_one(offer)
                    response = {'OK': 'Pubbliced.'}
                    # cerco se ci sono delle offerte di vendita che combaciano all'offerta di acquisto
                    check_offers(offer)
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
        # prelevo dal database tutti gli ordini eseguiti
        total_offer_closed = db.orders.find({'gain_bit': {'$exists': True}})
        # converto l'oggetto BSON in JSON
        total_offer_closed = json.loads(json_util.dumps(total_offer_closed))
        total_gain_lose_for_user = dict()
        # controllo tutte le informazioni incrementando/decementando in base al tipo di offerta la quantità di bit e fiat
        for offer in total_offer_closed:
            user = offer.get('user')
            type_offer = offer.get('type_offer')
            bit = offer.get('gain_bit')
            fiat = offer.get('gain_fiat')
            if user in total_gain_lose_for_user:
                if type_offer == 'buy':
                    total_gain_lose_for_user[user]['bit'] += bit
                    total_gain_lose_for_user[user]['fiat'] += fiat
                else:
                    total_gain_lose_for_user[user]['bit'] += bit
                    total_gain_lose_for_user[user]['fiat'] += fiat
            else:
                if type_offer == 'buy':
                    total_gain_lose_for_user[user] = dict({'bit': bit, 'fiat': fiat})
                else:
                    total_gain_lose_for_user[user] = dict({'bit': bit, 'fiat': fiat})
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


@csrf_exempt
def delete_order(request):
    '''Funzione che cancella un ordine ancora aperto.'''
    if request.method != 'POST':
        response = {'Error': 'Request type is wrong.'}
    elif str(request.user) == 'AnonymousUser':
        response = {'Error': 'No one is sing in.'}
    else:
        form = OrderId(request.POST)
        if form.is_valid():
            id = form.cleaned_data.get('id_order')
            string_object_order = ObjectId(id)
            amount_order = db.orders.count_documents({'_id': string_object_order})
            if amount_order > 0:
                order = db.orders.find({'_id': string_object_order})[0]
                if order.get('open_operation') == True:
                    if order.get('user') == str(request.user):
                        db.orders.update_one({'_id': string_object_order}, {'$set': {'amount_bit.available': 0,
                                                                                'open_operation': False,
                                                                                'close_operation_date': datetime.now()}})
                        response = {'OK': 'Your order is closed.'}
                    else:
                        response = {'Error': "That isn't your order."}
                else:
                    response = {'Error': "Order already closed."}
            else:
                response = {'Error': "Order doesn't exist."}
        else:
            response = {'Error': 'Compile the field.'}
    return JsonResponse(response, safe=False)


# creo un oggetto globale per poter comunicare con il database Mongo dove salvo le offerte
client = MongoClient('localhost', 27017)
db = client.exchange_platform
