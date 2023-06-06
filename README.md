## Описание
Блог. Позволяет создавать и комментировать посты, объединять их в группы, подписываться на авторов, просматривать группы и подписки.


## Как запустить проект: 

Клонировать репозиторий и перейти в него в командной строке: 

``` 
git clone https://github.com/OGURETS13/yatube.git
``` 


Cоздать и активировать виртуальное окружение: 

``` 

python3 -m venv env 

``` 

 

``` 

source env/bin/activate 

``` 

 

Установить зависимости из файла requirements.txt: 

 

``` 

python3 -m pip install --upgrade pip 

``` 

 

``` 

pip install -r requirements.txt 

``` 

 

Выполнить миграции: 

 

``` 

python3 manage.py migrate 

``` 

 

Запустить проект: 

 

``` 

python3 manage.py runserver 

``` 