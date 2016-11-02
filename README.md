# DonantesMalagaBot
DonantesMalagaBot es un Bot de Telegram basado en <a href="https://github.com/eternnoir/pyTelegramBotAPI">pyTelegramBotAPI</a> que facilita informacion a los donantes de Malaga acerca de los lugares donde se puede donar en el dia de hoy o en los proximos dias. Tambien lleva la cuenta sobre cuando se ha donado por ultima vez y permite al donante saber exactamente cuando puede volver a donar.

<p>
Puedes iniciar <a href="https://telegram.me/DonantesMalagaBot">DonantesMalagaBot</a> en Telegram pinchando en el siguiente enlace - https://telegram.me/DonantesMalagaBot
</p>

## Comandos soportados
<p>
Los comandos que soporta el Bot son los siguientes:
</p>

<ul>
<li>/dondehoy - conocer los puntos de donacion en el dia de hoy y los horarios</li>
<li>/dondeproximamente - conocer los puntos de donacion en los proximos dias</li>
<li>/hedonadohoy - hoy he donado sangre, asi que quiero recibir una notificacion cuando pueda volver a donar</li>
<li>/puedodonar - permite saber si puedo donar hoy en base a la fecha de ultima donacion conocida</li>
<li>/help - muestra esta lista de comandos</li>
</ul>

## Dependencias
Para el desarrollo de este Bot de Telegram se han utilizado las siguientes librerias:
<ul>
<li>pyTelegramBotAPI - hace de interfaz con la API de Telegram y proporciona toda la funcionalidad requerida para poder interactuar con Telegram</li>
<li>BeautifulSoup - utilizado para parsear la informacion de los puntos de donacion de la pagina web de www.donantesmalaga.org</li>
<li>MySQLdb - para interactuar con una base de datos MySQL que guarda la fecha de ultima de donacion del donante bajo demanda</li>
</ul>

## Contacto
<p>
Puedes contactarme a traves de Telegram - <a href="https://telegram.me/checheno">@checheno</a>
</p>
