Configuration de la messagerie
==============================

     Menu Administration/Modules (conf.)/Paramètres de courrier & SMS

Vous pouvez configurer ici des réglages pour l'envoi de couriel et de SMS.

Configuration du couriel
------------------------

Le serveur SMTP permettra au logiciel d'envoyer directement des messages à vos contacts.
Configurez donc ici les règlages de votre serveur.
Vous pouvez également préciser un *Fichier privé DKIM* et *Sélecteur DKIM* afin de signer vos envois de courriel.
Les paramètres *durée (en min) d'un lot de courriel* et *nombre de courriels par lot* sont utilisés pour l'envoie des messages en publipostage.

Un bouton *Envoyer* permet de tester vos règlages en envoyant un courriel de test à un destinataire choisi.
Il existe des outils permettant de vérifier si vos messages respectent des règles afin d'éviter d'être considéré comme des 'pourriel'.
En autre, l'outil https://www.mail-tester.com (gratuit jusqu'à 3 fois par jour) vous permet, en envoyant un message à l'adresse précisée, de vous établir une note de confiance. 

Vous pouvez, entre autre, envoyer d'un nouveau mot de passe de connexion.
N'oubliez pas alors de préciser un petit message d'explication via le paramètre *Message de confirmation de connexion*.

Configuration du SMS
--------------------

En configurant un fournisseur de SMS, vous pourrez alors envoyer des SMS à vos contacts.

Pour chaque fournisseur, vous devrez préciser le champ "Expression d'analyse de numéro (SMS)".
Il correspond à une expression régulière afin de savoir comment transformer un numéro de téléphone en numéro international.
Par défaut, il correspond au numéro français: *^0([67][0-9]{8})$|+33{0}*

	Il vérifie que le numéro comporte 10 chiffres.
	Il commance par '06' ou '07'.
	Il remplacera le '0' par '+33'. 

Suivant les besoins et les demandes, d'autres fournisseurs pourront être ajoutés à l'avenir.

Mailjet SMS
```````````
Mailjet (https://www.mailjet.com/) est une entreprise française qui propose, entre autres, d'envoyer des SMS.

Pour utiliser ce fournisseur, vous devez créer un compte sur leur site web.

Rendez vous ensuite sur leur portail SMS (https://app.mailjet.com/sms) où vous pourrez configurer votre accès au SMS:

 - Générer votre token d'accès
 - Créditer votre solde de SMS prépayé

Notez que le coùt d'un SMS dépend de sa taille et de sa destination.

Vous devrez ensuite indiquer dans "Options pour fournisseur SMS" votre "api token" généré précédement
ainsi qu'un "alias" qui sera l'identifiant présent dans le SMS envoyé.

Une fois votre configuration terminer, un bouton *Envoyer* permet de tester vos règlages en envoyant un SMS de contrôle à un numéro choisi.
  
 
 