Configuration
=============

     Menu *Administration/Modules (conf.)/Configuration du règlement*
     
Ce menu vous permet de configurer les comptes courants et les moyens de paiement en usage dans votre structure.

 
Code bancaire
-------------

Dans cet écran, vous avez la possibilité d'enregistrer les références des différents comptes courants ouverts au nom de votre structure.
A l'aide du bouton "+ Ajouter", vous pouvez en créer un nouveau et spécifier : la désignation, le RIB (référence), le code bancaire associé, le journal de mouvement désiré et optionnellement un compte d'attente.
Les compte doivent être déjà ouvert dans le plan comptable de l'exercice comme compte de trésorerie.

Dans le cas où vous préciseriez un compte d'attente, les mouvemets comptables générés seront un peu différent.  
Cette option est à utiliser dans les règlements par chèque bancaire (ou assimilé comme des "bons" ou "tickets" subventionnés proposés par certaines collectivités locales).    

En effet, au moment de la saisi de votre règlement, l'écriture sera alors créé sur le compte d'attente.  
Vous serez alors invité d'utiliser l'outil de gestion de bordereaux de chèques et lors de la validation finale de celui-ci, 
une écriture générale réalisera le mouvement financier entre ce compte d'attente et le compte bancaire proprement dit. 

Moyen de paiement
-----------------

Vous pouvez ici préciser les moyens de paiement que vous acceptez.

Actuellement, 6 moyens de paiement sont possibles sous *Diacamma*, pour chacun d'entre eux, vous devez préciser les paramètres correspondants:

 - Le virement bancaire  
 - Le chèque  
 - Le paiement PayPal
   
 Dans le cas de PayPal, si votre *Diacamma* est accessible via le Net, le paiement de votre débiteur vous est notifié sous votre application et le règlement correspondant généré directement dans votre logiciel.
 Il est conseillé de cocher le champ *avec contrôle*. Ainsi, le lien de paiement présenté dans un courriel s'assurera dans un premier temps que, sous votre *Diacamma*, l'élément financier est toujours d'actualité.
  
 - Le règlement en ligne, via une adresse internet  
 - Le paiement MoneticoPaiement  
 
 Pour MoneticoPaiement, la plateforme de paiement du Crédit Mutuel et du CIC (voir https://www.monetico-paiement.fr), veuillez prendre contact avec votre agence bancaire pour faire ouvrir votre accès.
 Et si vous *Diacamma* est accessible via le Net, vous devez déclarer à la plateforme une adresse de retour de type "https://mon.site.diacamma/diacamma.payoff/validationPaymentMoneticoPaiement" ("https://mon.site.diacamma" étant l'adresse d'accès à votre serveur *Diacamma*)
 
 - Le paiement Hello-Asso  

 Pour utiliser la plateforme Hello-Asso pour réaliser vos paiements, connectez vous sur le portail https://www.helloasso.com. 
 Sur votre compte de structure, dans le menu "Mon compte > Intégration et API", vous devez recopiez les champs *mon clientid* et *mon clientsecret* dans l'interface.
 Et si votre *Diacamma* est accessible via le Net, le paiement de votre débiteur vous est notifié sous votre application et le règlement correspondant généré directement dans votre logiciel.

Ces moyens de paiement peuvent être utilisés par vos débiteurs, via précision en bas de couriel, pour régler ce qu'ils vous doivent.

Paramètres
----------

4 Paramètres actuellement :

 - compte de caisse : code comptable à mouvementer pour les règlements en espèces
 - compte de frais bancaires : code comptable devant être utilisé pour comptabiliser les frais bancaires liés aux règlements. Une ligne d'écriture est alors ajoutée directement à l'écriture comptable correspondante si le champ "compte de frais bancaires" est renseigné, ce qui permet de saisir le montant des frais.
 - sujet et message par défaut proposés à l'envoie des justificatifs d'un paiement.
