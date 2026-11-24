from django.contrib import admin

from validador.models import LoteGerado, Pagamento, Precatorio, ResolucaoRegistro

admin.site.register([Precatorio, Pagamento, ResolucaoRegistro, LoteGerado])
