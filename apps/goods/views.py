from django.shortcuts import render

# Create your views here.

# index
def index(request):
    '''显示首页'''
    return render(request, 'index.html')
