# DonantesMalagaBot

DonantesMalagaBot es un Bot de Telegram basado en [pyTelegramBotAPI](https://github.com/eternnoir/pyTelegramBotAPI) que facilita informacion a los donantes de Malaga acerca de los lugares donde se puede donar en el dia de hoy o en los proximos dias. Tambien lleva la cuenta sobre cuando se ha donado por ultima vez y permite al donante saber exactamente cuando puede volver a donar.

Puedes iniciar [DonantesMalagaBot](https://telegram.me/DonantesMalagaBot) en Telegram pinchando en el siguiente enlace - https://telegram.me/DonantesMalagaBot

## Comandos soportados

Los comandos que soporta el Bot son los siguientes:

- `/dondehoy` - conocer los puntos de donacion en el dia de hoy y los horarios
- `/dondeproximamente` - conocer los puntos de donacion en los proximos dias
- `/hedonadohoy` - hoy he donado sangre, asi que quiero recibir una notificacion cuando pueda volver a donar
- `/puedodonar` - permite saber si puedo donar hoy en base a la fecha de ultima donacion conocida
- `/help` - muestra esta lista de comandos

## Dependencias

Para el desarrollo de este Bot de Telegram se han utilizado las siguientes librerias:

- **pyTelegramBotAPI** - hace de interfaz con la API de Telegram y proporciona toda la funcionalidad requerida para poder interactuar con Telegram
- **BeautifulSoup** - utilizado para parsear la informacion de los puntos de donacion de la pagina web de www.donantesmalaga.org
- **MySQL-python** - para interactuar con una base de datos MySQL que guarda la fecha de ultima de donacion del donante bajo demanda

```
$ pip install pyTelegramBotAPI
$ pip install bs4
$ pip install MySQL-python
```

## Contacto

Puedes contactarme a traves de Telegram - [@checheno](https://telegram.me/checheno)

