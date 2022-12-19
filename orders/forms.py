from django import forms


class Order(forms.Form):
    amount_bit = forms.IntegerField()
    amount_fiat = forms.IntegerField()
    type_offer = forms.CharField(max_length=4)


class Convert(forms.Form):
    fiat = forms.IntegerField()


class OrderId(forms.Form):
    id_order = forms.CharField()
