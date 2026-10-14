# -*- coding: utf-8 -*-
'''
Printmodel django module for dummy

@author: Laurent GAY
@organization: sd-libre.fr
@contact: info@sd-libre.fr
@copyright: 2016 sd-libre.fr
@license: This file is part of Lucterios.

Lucterios is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Lucterios is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Lucterios.  If not, see <http://www.gnu.org/licenses/>.
'''

from __future__ import unicode_literals

name = "mailing"
kind = 2
modelname = 'mailing.Message'
value = """
<model hmargin="10.0" vmargin="10.0" page_width="210.0" page_height="297.0">
<header extent="25.0">
<text height="20.0" width="120.0" top="5.0" left="70.0" padding="1.0" spacing="0.0" border_color="black" border_style="" border_width="0.2" text_align="center" line_height="20" font_family="sans-serif" font_weight="" font_size="20">
{[b]}#OUR_DETAIL.name{[/b]}
</text>
<image height="25.0" width="30.0" top="0.0" left="10.0" padding="1.0" spacing="0.0" border_color="black" border_style="" border_width="0.2">
#OUR_DETAIL.image
</image>
</header>
<bottom extent="10.0">
<text height="10.0" width="190.0" top="00.0" left="0.0" padding="1.0" spacing="0.0" border_color="black" border_style="" border_width="0.2" text_align="center" line_height="8" font_family="sans-serif" font_weight="" font_size="8">
{[i]}#OUR_DETAIL.address #OUR_DETAIL.postal_code #OUR_DETAIL.city - #OUR_DETAIL.tel1 #OUR_DETAIL.email{[br/]}
#OUR_DETAIL.identify_number
{[/i]}
</text>
</bottom>
<body>
<text height="20.0" width="100.0" top="25.0" left="80.0" padding="1.0" spacing="0.0" border_color="black" border_style="" border_width="0.2" text_align="center" line_height="11" font_family="sans-serif" font_weight="" font_size="11">
{[b]}#contact.str{[/b]}{[br/]}
#contact.address{[br/]}
#contact.postal_code #contact.city
</text>
<text height="20.0" width="130.0" top="55.0" left="20.0" padding="1.0" spacing="0.0" border_color="black" border_style="" border_width="0.2">
{[u]}#subject{[/u]}
</text>
<text height="20.0" width="40.0" top="55.0" left="150.0" padding="1.0" spacing="0.0" border_color="black" border_style="" border_width="0.2">
{[i]}#date{[/i]}
</text>
<text data="line_set" height="5.0" width="190.0" top="80.0" left="0.0" padding="1.0" spacing="0.1" border_color="black" border_style="" border_width="0.2">
#line
</text>
</body>
</model>
"""
