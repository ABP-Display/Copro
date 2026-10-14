Configuration
=============

Menu "Administration/Payoff configuration" allows you some configurations for your structure.

Bank account
------------

In this screen, you can record your various bank accounts you have.
For each, you can enter all of the information on a RIB.
This will allow you to edit a comprehensive summary of your check deposits.

Payment method
--------------

Here you can specify the means of payment that you support.
Currently, 3 methods of payment are taken into account by _Diacamma_
  - Bank transfer
  - The check
  - The PayPal payment
For each of them, you must specify the relative parameters.

It is a means of payment can be used for your debtors to settle by its means what they owe you.
In the case of PayPal, if your _Diacamma_ is accessible via the Internet, the software can be communicated directly to the payment and add a corresponding payment.

Parameters
----------

Currently two parameters:
 - cash Account: indicates the account code to charge for payments in cash.
 - bank charges account: a precise accounting code to directly post, following a settlement, bank charges inherent in this settlement.
A write line is added directly to the corresponding accounting entry.
If this code is empty, no bank charges will be requested.
