from django.shortcuts import render
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import login, authenticate, logout
from django.http import JsonResponse
from .forms import LoginForm, RegisterForm, Charge
from pymongo import MongoClient
from random import randint
from bson import json_util
import json


# Create your views here.
@csrf_exempt
def sing_in(request):
    '''Funzione che riceve una richiesta POST e ritorna un oggetto JSON in base se l'utente si è loggato oppure non esiste'''
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user:
                login(request, user)
                response = {'OK': 'Logged'}
            else:
                response = {'Error': "User doesn't exist. Create a new user."}
    else:
        response = {'Error': 'You have to send the POST request'}
    return JsonResponse(response, safe=False)


@csrf_exempt
def sing_up(request):
    '''Funzione che riceve una richiesta POST e crea un nuovo utente assegnandoli una quantità casuale tra 1 e 10 di bitcoin e tra 40 e 60
    di fiat'''
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            db.users.insert_one({'user': f'{str(user)}', 'bit_balance': randint(1, 10), 'fiat_balance': randint(40, 60)})
            response = {'OK': 'User create and logged'}
        else:
            if User.objects.filter(username=request.POST.get('username')):
                response = {'Error': 'User already exist.'}
            else:
                response = {'Error': 'Data wrongs.'}
    return JsonResponse(response, safe=False)


@csrf_exempt
def user_logout(request):
    '''Riceve una richiesta POST e slogga l'utente'''
    if request.method == 'POST':
        if str(request.user) != 'AnonymousUser':
            logout(request)
            response = {'OK': 'User logout.'}
        else:
            response = {'Error': 'No one sing in.'}
    return JsonResponse(response, safe=False)


@csrf_exempt
def charge_account(request):
    '''Funzione che ricarica l'account'''
    if request.method == 'POST' and str(request.user) != 'AnonymousUser':
        form = Charge(request.POST)
        if form.is_valid():
            fiat = form.cleaned_data.get('fiat')
            db.users.update_one({'user': str(request.user)}, {'$set': {'fiat_balance': fiat}})
            response = {'OK': 'Balance update.'}
        else:
            response = {'Error': 'Missing field.'}
    else:
        response = {'Error': 'No one sing in.'}
    return JsonResponse(response, safe=False)


def get_users(request):
    '''Funzione che ritorna una lista con i nomi di tutti gli utenti registrati'''
    if request.method == 'GET':
        total_users = db.users.find({}, {'user': 1})
        # converto l'oggetto BSON in JSON
        total_users = json.loads(json_util.dumps(total_users))
        list_users = list()
        for user in total_users:
            list_users.append(user.get('user'))
        return JsonResponse(list_users, safe=False)


def get_user_account(request):
    '''Funzione che ritorna tutti i dati dell'account dell'utente registrato'''
    if request.method != 'GET':
        response = {'Error': 'Request type is wrong.'}
    elif str(request.user) == 'AnonymousUser':
        response = {'Error': 'No one is sing in.'}
    else:
        user = db.users.find({'user': str(request.user)})
        # converto l'oggetto BSON in JSON
        user = json.loads(json_util.dumps(user))[0]
        del user['_id']
        response = user
    return JsonResponse(response, safe=False)


# creo un oggetto globale per poter comunicare con il database Mongo dove salvo le offerte
client = MongoClient('localhost', 27017)
db = client.exchange_platform