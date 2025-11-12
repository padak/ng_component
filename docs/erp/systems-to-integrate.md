# ERP Systems Integration Guide

**Last Updated:** 2025-11-11
**Purpose:** Comprehensive implementation roadmap for ERP system integrations with Keboola

---

## 📋 Executive Summary

### Implementation Priority

1. **Quick Wins (1-2 týdny)** - 4 systémy ✅
2. **Střední náročnost (2-4 týdny)** - 4 systémy
3. **Custom Development (4-6+ týdnů)** - 8 systémů

### Recommended Approach for Neobank

**Fáze 1 - Rychlá implementace (3 týdny po specifikaci):**
- FlexiBee ✅
- MS Dynamics Business Central ✅
- K2 (Karat) ✅
- Fakturoid ✅

**Fáze 2 - Rozšíření (další 2-4 týdny):**
- Pohoda Cloud (mPOHODA)
- QuickBooks Online
- Xero

**Fáze 3 - Custom development (4-6+ týdnů):**
- Money S3/S4/S5
- Helios iNuvio
- Rakouské systémy (BMD, RZL, Mesonic, Sage)
- SAP Business One

---

## ✅ Quick Wins (1-2 týdny)

Systémy, které jsou buď plně připraveny nebo vyžadují minimální setup.

### FlexiBee (ABRA Flexi)

**Status:** ✅ Máme konektor
**Priorita:** HIGH
**Časová náročnost:** Připraveno
**Keboola typ:** Data source

#### API Přehled
- **Typ:** REST API
- **Formát:** JSON/XML
- **Autentizace:** Basic auth nebo token
- **Dokumentace:** https://www.flexibee.eu/abra-flexibee-api-z-prikazove-radky/

#### Získání Demo/Sandbox přístupu

**Veřejný demo server:**
- URL: `demo.flexibee.eu`
- Login: `winstrom`
- Password: `winstrom`
- Umožňuje čtení i zápis dat
- ✅ Okamžitý přístup bez registrace

**Kroky pro vlastní testování:**
1. Použij veřejný demo server (okamžitý přístup)
2. Nebo získej **bezplatnou vývojářskou licenci na 3 měsíce** pro lokální instalaci
3. Registrace: https://www.flexibee.eu/api/licence-pro-vyvojare/

#### Implementační poznámky

**Features:**
- ✅ REST API s CRUD operacemi
- ✅ Webhooky pro real-time notifikace
- ✅ Podpora master data sync (účty, nákladová střediska)
- ✅ Export faktur

**Gotchas:**
- ⚠️ Od 2025 vyžaduje produkční API placenou licenci
- 💡 Demo server je perfektní pro development
- 💡 API má granulární práva na úrovni objektů

**Keboola integrace:**
- FlexiBee component je dostupný v Keboola
- Použití: Direct component (ne Generic Extractor)

**Užitečné odkazy:**
- API dokumentace: https://www.flexibee.eu/abra-flexibee-api-z-prikazove-radky/
- Licence pro vývojáře: https://www.flexibee.eu/api/licence-pro-vyvojare/
- Licencování API: https://podpora.flexibee.eu/cs/articles/10097467-licencovani-pristupu-k-api

---

### K2 (Karat)

**Status:** ✅ Máme konektor
**Priorita:** HIGH
**Časová náročnost:** Připraveno
**Keboola typ:** Data source

#### API Přehled
- **Typ:** REST API přes K2 Server of Web Services (SWS)
- **Formát:** JSON (default) nebo XML
- **Metody:** HTTP GET/POST/PUT
- **Autentizace:** API user s anonymním prefixem
- **Dokumentace:** https://help.k2.cz/k2luna/12/en/10010133.htm

#### Získání Demo/Sandbox přístupu

**Požadavky:**
- Vlastní instalace K2 (není veřejný sandbox)
- Licence "SWS thread" v K2
- Konfigurace služby na IIS

**Kroky:**
1. Kontaktuj K2 vendor pro demo instalaci
2. Zakup licenci "SWS thread"
3. Nakonfiguruj Web Services na IIS
4. Vytvoř API uživatele s anonymním prefixem

#### Implementační poznámky

**Features:**
- ✅ REST API s JSON/XML podporou
- ✅ Master data sync
- ✅ Export faktur a dokladů

**Gotchas:**
- ⚠️ Vyžaduje vlastní instalaci K2
- ⚠️ Nutná licence SWS thread
- ⚠️ API uživatel musí mít anonymní prefix
- 💡 Detaily poskytuje vendor na vyžádání

**Keboola integrace:**
- K2 component je dostupný v Keboola
- Custom connector

**URL format:**
```
.../<xml>/<service>/<resource>{?parameters}
```

**Užitečné odkazy:**
- Dokumentace: https://help.k2.cz/k2luna/12/en/10010133.htm

---

### Fakturoid

**Status:** ✅ Plně podporováno
**Priorita:** HIGH
**Časová náročnost:** 1-2 týdny
**Keboola typ:** Source + Destination

#### API Přehled
- **Typ:** REST API v3
- **Formát:** JSON
- **Autentizace:** OAuth 2.0 (Authorization Code + Client Credentials)
- **Endpoint:** `https://app.fakturoid.cz/api/v3`
- **Dokumentace:** https://www.fakturoid.cz/api/v3

#### Získání Demo/Sandbox přístupu

**Přístup:**
- Žádný veřejný sandbox
- Doporučeno: vytvořit dvě integrace (test + prod) ve vlastním účtu

**Kroky:**
1. Vytvoř účet na Fakturoid.cz
2. V nastavení účtu vytvoř novou integraci
3. Získej Client ID a Client Secret
4. Implementuj OAuth 2.0 flow
5. Vytvoř separátní integraci pro testování

#### Implementační poznámky

**Features:**
- ✅ Moderní REST API v3
- ✅ OAuth 2.0 autentizace
- ✅ Source i Destination (read + write)
- ✅ Snadná implementace

**Gotchas:**
- ⚠️ Vyžaduje `User-Agent` hlavičku v každém requestu
- 💡 OAuth 2.0 Authorization Code flow pro user consent
- 💡 Client Credentials pro machine-to-machine

**Keboola integrace:**
- Plně podporováno
- Použití: Direct component nebo Generic Extractor

**OAuth 2.0 Flows:**
- Authorization Code: Pro user-initiated akce
- Client Credentials: Pro backend integrace

**Užitečné odkazy:**
- API v3: https://www.fakturoid.cz/api/v3
- Authorization: https://www.fakturoid.cz/api/v3/authorization

---

### Pohoda Cloud (mPOHODA)

**Status:** 💡 Generic Extractor/Writer možné
**Priorita:** HIGH
**Časová náročnost:** 1-2 týdny
**Keboola typ:** Generic Extractor + Writer

#### API Přehled
- **Typ:** REST API (cloudová verze)
- **Formát:** JSON
- **Endpoint:** `https://api.mpohoda.cz/v1`
- **Metody:** GET/POST/PUT/DELETE
- **Autentizace:** API klíče nebo OAuth 2.0
- **Dokumentace:** https://api.mpohoda.cz/doc/quick-start

#### Získání Demo/Sandbox přístupu

**Požadavky:**
- Předplatné mPOHODA Pro (placený tarif)
- Není veřejný sandbox

**Kroky:**
1. Objednej mPOHODA Pro tarif
2. V nastavení účtu vygeneruj API klíče
3. Nebo nastav OAuth 2.0 token
4. Testuj na vlastním účtu

#### Implementační poznámky

**Features:**
- ✅ REST API v cloudu
- ✅ ReDoc/Swagger dokumentace
- ✅ Master data sync
- ✅ Export faktur

**Gotchas:**
- ⚠️ Vyžaduje placený tarif Pro
- ⚠️ Není veřejný sandbox
- 💡 Quick-start dokumentace je dobrá
- 💡 Cloud verze je rychlejší než on-prem (mServer)

**Keboola integrace:**
- Generic Extractor + Writer
- REST API je dobře strukturované

**Knihovny:**
- Seznam dostupných knihoven: https://api.mpohoda.cz/doc/general/other/libraries

**Užitečné odkazy:**
- Quick-start: https://api.mpohoda.cz/doc/quick-start
- Knihovny: https://api.mpohoda.cz/doc/general/other/libraries

---

## ⚠️ Střední náročnost (2-4 týdny)

Systémy vyžadující komplexnější setup nebo vendor spolupráci.

### MS Dynamics 365 Business Central

**Status:** ✅ Máme konektor
**Priorita:** HIGH (právě launchli)
**Časová náročnost:** 2-4 týdny
**Keboola typ:** Data source + destination

#### API Přehled
- **Typ:** REST API (OData v2.0)
- **Účel:** Connect Apps
- **Metody:** HTTP GET/POST/PATCH/DELETE
- **Autentizace:** OAuth 2.0 (Azure AD)
- **Dokumentace:** https://learn.microsoft.com/en-us/dynamics365/business-central/dev-itpro/api-reference/v2.0/

#### Získání Demo/Sandbox přístupu

**Sandbox prostředí:**
- K dispozici v rámci Business Central
- Obsahuje demo firmu CRONUS
- Preview sandbox pro vývoj

**Kroky:**
1. Objednej Business Central předplatné
2. V administraci tenanta vytvoř sandbox
3. Registruj Azure aplikaci pro OAuth 2.0
4. Nastav granulární práva (scopes)
5. Použij CRONUS demo firmu pro testování

#### Implementační poznámky

**Features:**
- ✅ Standardní REST API
- ✅ OData v2.0 protokol
- ✅ Čtení i zápis dat
- ✅ Sandbox s demo daty

**Gotchas:**
- ⚠️ Komplexní OAuth 2.0 setup (Azure AD)
- ⚠️ Granulární práva - musí se správně nastavit
- 💡 Sandbox doporučen pro development
- 💡 CRONUS firma má realistická testovací data

**Keboola integrace:**
- Právě launchli (viz changelog)
- Pro Financial Intelligence solution
- Direct component

**Užitečné odkazy:**
- API v2.0: https://learn.microsoft.com/en-us/dynamics365/business-central/dev-itpro/api-reference/v2.0/
- Sandbox setup: https://www.kristenhosman.com/setting-up-a-sandbox-environment-in-dynamics-365-business-central
- Keboola changelog: https://changelog.keboola.com/
- Solution: https://www.keboola.com/solutions/financial-intelligence

---

### Pohoda on-prem (mServer)

**Status:** 💡 Možné přes Generic
**Priorita:** MEDIUM
**Časová náročnost:** 2-4 týdny
**Keboola typ:** Generic Extractor + Writer (komplexní)

#### API Přehled
- **Typ:** HTTP server (mServer)
- **Formát:** XML DataPack
- **Protokol:** Request-Response XML
- **Autentizace:** Konfigurace v mServer
- **Dokumentace:** https://www.stormware.cz/pohoda/xml/mserver/

#### Získání Demo/Sandbox přístupu

**Požadavky:**
- Lokální instalace Pohody on-prem
- Instalace a konfigurace mServer
- Často přístup přes VPN/SSH tunnel

**Kroky:**
1. Instaluj Pohodu on-prem
2. Instaluj mServer addon
3. Nakonfiguruj mServer (port, přístupová práva)
4. Nastav VPN/SSH tunnel pro remote přístup
5. Testuj XML DataPack kommunikaci

#### Implementační poznámky

**Features:**
- ✅ HTTP server pro XML komunikaci
- ✅ Request-response pattern
- ✅ Master data sync
- ✅ Export faktur

**Gotchas:**
- ⚠️ XML DataPack formát je složitější než REST/JSON
- ⚠️ Vyžaduje VPN/SSH tunnel pro remote přístup
- ⚠️ Instalace a konfigurace mServeru není triviální
- ⚠️ API není veřejně otevřené
- 💡 Cloud verze (mPOHODA) je rychlejší cesta!

**Keboola integrace:**
- Generic Extractor + Writer
- Vyžaduje custom XML parsing

**Doporučení:**
- 💡 Pokud možno, preferuj mPOHODA cloud verzi (rychlejší, jednodušší)

**Užitečné odkazy:**
- mServer dokumentace: https://www.stormware.cz/pohoda/xml/mserver/

---

### QuickBooks Online

**Status:** ✅ Připraveno
**Priorita:** MEDIUM
**Časová náročnost:** 2-3 týdny
**Keboola typ:** Data source

#### API Přehled
- **Typ:** REST API
- **Prostředí:** Sandbox + Production
- **Autentizace:** OAuth 2.0
- **Dokumentace:** Intuit Developer Portal

#### Získání Demo/Sandbox přístupu

**Sandbox:**
- Automaticky vytvoří po registraci vývojářského účtu
- Obsahuje "sample company" s testovacími daty
- Oddělené klíče od produkce

**Kroky:**
1. Registruj se na Intuit Developer Portal
2. Vytvoř aplikaci (získáš Client ID/Secret)
3. Sandbox se vytvoří automaticky
4. Použij sandbox klíče pro testování
5. Implementuj OAuth 2.0 flow

#### Implementační poznámky

**Features:**
- ✅ REST API
- ✅ Automatický sandbox s daty
- ✅ OAuth 2.0
- ✅ Oddělené dev/prod prostředí

**Python SDK:**
- Komunitní knihovna: `python-quickbooks`
- PyPI: https://pypi.org/project/python-quickbooks/

**Gotchas:**
- ⚠️ Sandbox používá jiné klíče než produkce
- 💡 Sample company má realistická data
- 💡 Sandbox se automaticky vytváří

**Keboola integrace:**
- Component dostupný
- Nebo Generic Extractor

**Užitečné odkazy:**
- Intuit Developer Portal: (viz dokumentace)
- Python SDK: https://pypi.org/project/python-quickbooks/
- Setup guide: https://docs.codat.io/integrations/accounting/quickbooksonline/accounting-quickbooksonline-new-setup

---

### Xero

**Status:** ✅ Beta
**Priorita:** MEDIUM
**Časová náročnost:** 2-3 týdny
**Keboola typ:** Data source (Xero Accounting V2)

#### API Přehled
- **Typ:** REST API
- **Autentizace:** OAuth 2.0
- **Oblasti:** Účetnictví, majetek, soubory, projekty
- **Dokumentace:** Xero Developer Portal

#### Získání Demo/Sandbox přístupu

**Demo Company:**
- Xero poskytuje "Demo Company"
- Resetuje se každých 28 dní
- Plně funkční pro testování

**Kroky:**
1. Vytvoř účet na Xero
2. Registruj vývojářskou aplikaci
3. Vyber scopes (permissions)
4. Získej OAuth 2.0 tokeny
5. Použij Demo Company pro testování

#### Implementační poznámky

**Features:**
- ✅ REST API s OAuth 2.0
- ✅ Demo Company (reset každých 28 dní)
- ✅ Oficiální Python SDK
- ✅ Kompletní funkcionalita

**Python SDK:**
- Oficiální: `xero-python`
- PyPI: https://pypi.org/project/xero-python/
- Pokrývá celou funkcionalitu API

**Gotchas:**
- ⚠️ Demo Company se resetuje každých 28 dní
- 💡 Oficiální Python SDK je kvalitní
- 💡 Scopes se volí při registraci aplikace

**Keboola integrace:**
- Xero Accounting V2 (Beta)
- Generic Extractor možné

**Užitečné odkazy:**
- Developer Portal: (Xero Developer)
- Python SDK: https://pypi.org/project/xero-python/
- Demo Company reset: https://productideas.xero.com/forums/939198-for-small-businesses/suggestions/47086372-demo-company-reset-date-countdown

---

## 🔧 Custom Development (4-6+ týdnů)

Systémy vyžadující vývoj custom konektoru nebo vendor spolupráci.

### České systémy

#### Money S3/S4/S5

**Status:** ❌ Nemáme
**Priorita:** MEDIUM
**Časová náročnost:** 1-2 týdny (s modulem)
**Keboola typ:** Custom Extractor + Writer

##### API Přehled
- **Typ:** GraphQL API
- **Operace:** Read (synchronní) + Write (asynchronní)
- **Autentizace:** Client ID + Secret
- **Požadavky:** Zakoupený API modul
- **Dokumentace:** https://money.cz/navod/api-v-money-s3-pro-vyvojare/

##### Získání Demo/Sandbox přístupu

**Požadavky:**
- Vlastní instalace Money S3
- Zakoupený modul API
- Registrace aplikace v Money S3

**Kroky:**
1. Instaluj Money S3
2. Zakup modul API
3. V aplikaci vygeneruj Client ID a Secret
4. Registruj aplikaci pro API přístup
5. Testuj GraphQL queries

##### Implementační poznámky

**Features:**
- ✅ GraphQL API (read + write)
- ✅ Master data sync (účty, nákladová střediska)
- ✅ Export faktur
- ✅ README dokumentuje import voucher/facture

**Gotchas:**
- ⚠️ Vyžaduje zakoupený modulu API
- ⚠️ Žádný veřejný sandbox
- ⚠️ Čtení synchronní, zápis asynchronní
- 💡 Custom setup potřebný (module purchase)

**Keboola integrace:**
- Custom Extractor + Writer
- GraphQL komunikace

**Užitečné odkazy:**
- API návod: https://money.cz/navod/api-v-money-s3/?utm_source=chatgpt.com
- Pro vývojáře: https://money.cz/navod/api-v-money-s3-pro-vyvojare/

---

#### Helios iNuvio

**Status:** ❌ Nemáme
**Priorita:** LOW
**Časová náročnost:** 3-4 týdny
**Keboola typ:** Custom connector (vendor API access)

##### API Přehled
- **Typ:** REST API (modern, rumored)
- **Server:** Inuvio Server
- **Moduly:** Auth API, OAuth2 API, System API, e-shop API
- **Autentizace:** API přes Inuvio Server
- **Dokumentace:** https://public.helios.eu/inuvio/doc/cs/index.php

##### Získání Demo/Sandbox přístupu

**Požadavky:**
- Instalace Inuvio Serveru
- Licence Helios iNuvio
- Vendor spolupráce

**Kroky:**
1. Kontaktuj Helios vendor
2. Získej instalaci Inuvio Serveru
3. Zakup licenci
4. Nastav API moduly
5. Specifikace je offline (pouze pro zákazníky)

##### Implementační poznámky

**Features:**
- ✅ Modern REST API (rumored for iNuvio)
- ✅ Moduly: Auth, OAuth2, System, e-shop
- ✅ Master data + invoice export viable

**Gotchas:**
- ⚠️ Vyžaduje vendor spolupráci
- ⚠️ Méně veřejné dokumentace
- ⚠️ Přístup jen pro zákazníky
- ⚠️ Může vyžadovat custom connector
- 💡 Alternativa: DB access nebo export skripty

**Keboola integrace:**
- Custom connector
- Vyžaduje vendor API access

**Užitečné odkazy:**
- REST API úvod: https://public.helios.eu/inuvio/doc/cs/index.php?title=%C3%9Avod_-_REST_API

---

### Rakouské systémy

#### BMD (Rakousko)

**Status:** ❌ Nepřipraveno
**Priorita:** LOW
**Časová náročnost:** 4-6 týdnů (partner required)
**Keboola typ:** Custom connector

##### API Přehled
- **Typ:** SOAP/XML
- **Přístup:** Partner-only
- **Funkcionalita:** Data import/export with certification
- **Autentizace:** Partner credentials

##### Získání Demo/Sandbox přístupu

**Požadavky:**
- Partnerství s BMD
- Certifikace

**Kroky:**
1. Kontaktuj BMD pro partnerství
2. Projdi certifikací
3. Získej partner API credentials
4. Není veřejný sandbox

##### Implementační poznámky

**Features:**
- ✅ Data import/export
- ⚠️ Limited (SOAP/XML APIs)

**Gotchas:**
- ⚠️ API přístup pouze pro partnery
- ⚠️ Vyžaduje certifikaci
- ⚠️ Bez spolupráce není API dostupné
- 💡 Custom connector nutný

**Keboola integrace:**
- Custom connector
- Vyžaduje vendor partnerství

---

#### RZL (Rakousko)

**Status:** ❌ Nepřipraveno
**Priorita:** LOW
**Časová náročnost:** ? (Žádné public info)
**Keboola typ:** Manual file exchange

##### API Přehled
- **Typ:** Žádné veřejné API
- **Integrace:** CSV/XML import/export
- **Automatizace:** Scheduled exports možné

##### Získání Demo/Sandbox přístupu

**Žádný sandbox:**
- Není API
- Pouze ruční export/import

##### Implementační poznámky

**Features:**
- ⚠️ CSV/XML import/export možné
- ⚠️ Scheduled exports

**Gotchas:**
- ❌ Žádné veřejné API
- 💡 Řešení přes automatizované exporty souborů

**Keboola integrace:**
- Manual file exchange
- Scheduled file imports

---

#### Mesonic WinLine (Rakousko)

**Status:** ❌ Nepřipraveno
**Priorita:** LOW
**Časová náročnost:** 4-6 týdnů
**Keboola typ:** Custom connector

##### API Přehled
- **Typ:** Import/export nástroje
- **Moduly:** EXIM, Batch Voucher
- **Formáty:** ODBC, ASCII, XLS, MDB
- **Autentizace:** License required
- **Dokumentace:** https://www.mesonic.com/systemtoolsen

##### Získání Demo/Sandbox přístupu

**Požadavky:**
- Instalace WinLine
- Licence modulu EXIM
- Není veřejný sandbox

**Kroky:**
1. Získej WinLine instalaci
2. Zakup licenci modulu EXIM
3. Nakonfiguruj import/export nástroje

##### Implementační poznámky

**Features:**
- ✅ Import/export moduly
- ✅ ODBC, ASCII, XLS, MDB formáty

**Gotchas:**
- ⚠️ API moduly vyžadují licensing
- ⚠️ Není open by default
- ⚠️ Není veřejné API
- 💡 Custom connector nutný

**Keboola integrace:**
- Custom connector
- File-based integration možné

**Užitečné odkazy:**
- System tools: https://www.mesonic.com/systemtoolsen

---

#### Sage 50 / Sage AT (Rakousko)

**Status:** ❌ Nepřipraveno
**Priorita:** LOW
**Časová náročnost:** Neurčeno
**Keboola typ:** Generic Extractor + Writer (třetí strana)

##### API Přehled
- **Typ:** Žádné oficiálně otevřené API
- **Třetí strana:** HyperAccounts REST API
- **Autentizace:** API key od HyperAccounts
- **Dokumentace:** https://sage-50-accounts-api-v1-docs.hyperext.com/

##### Získání Demo/Sandbox přístupu

**Požadavky:**
- Kontakt s HyperAccounts (third-party provider)
- API tokeny vydává HyperAccounts
- Demoverze není

**Kroky:**
1. Kontaktuj HyperAccounts
2. Získej API klíč
3. Potvrď Austrian instance kompatibilitu

##### Implementační poznámky

**Features:**
- ✅ REST APIs pro accounting (přes třetí stranu)
- ⚠️ Není oficiální API od Sage

**Gotchas:**
- ⚠️ Nutný kontakt s třetí stranou (HyperAccounts)
- ⚠️ Potvrdit Austrian instance support
- 💡 Generic Extractor možné

**Keboola integrace:**
- Generic Extractor + Writer
- Přes HyperAccounts API

**Užitečné odkazy:**
- HyperAccounts: https://sage-50-accounts-api-v1-docs.hyperext.com/

---

### Enterprise systémy

#### SAP Business One

**Status:** ✅ Máme konektor
**Priorita:** MEDIUM
**Časová náročnost:** Připraveno (vendor collaboration)
**Keboola typ:** Custom (připraveno ve spolupráci s vendorem, otestováno na Fast.cz)

##### API Přehled
- **Typ:** Service Layer (REST/OData API)
- **Verze:** Pro SAP HANA
- **Protokoly:** HTTP, OData
- **Operace:** GET/POST/PATCH/DELETE (CRUD)
- **Core:** DI Core objekty
- **Autentizace:** Login k SAP B1 systému
- **Dokumentace:** https://cdn2.hubspot.net/hubfs/38093/Content_Library/Report/Training/Working%20with%20SAP%20Business%20One%20Service%20Layer...

##### Získání Demo/Sandbox přístupu

**Požadavky:**
- Licence SAP Business One
- Instalace Service Layer na serveru (vyžaduje SAP HANA)
- Není veřejný sandbox

**Kroky:**
1. Získej licenci SAP B1
2. Instaluj Service Layer na SAP HANA
3. Nakonfiguruj autentizaci
4. Testuj CRUD operace přes OData

##### Implementační poznámky

**Features:**
- ✅ Service Layer – REST/OData API
- ✅ CRUD operace
- ✅ DI Core objekty
- ✅ Připraveno ve spolupráci s vendorem

**Gotchas:**
- ⚠️ Vyžaduje SAP HANA
- ⚠️ Nutná licence SAP B1
- ⚠️ Instalace Service Layer na serveru
- ⚠️ Není veřejný sandbox
- 💡 Otestováno na Fast.cz

**Keboola integrace:**
- Custom component připraven
- Otestováno ve spolupráci s vendorem

**Užitečné odkazy:**
- Service Layer manual: Working with SAP Business One Service Layer (SAP HANA version)

---

## 📚 Keboola Integration Reference

### Integration Approaches

#### 1. Direct Components
Připravené Keboola komponenty pro konkrétní systémy:
- **FlexiBee** ✅
- **MS Dynamics 365 BC** ✅
- **K2 (Karat)** ✅
- **SAP Business One** ✅
- **Fakturoid** ✅
- **QuickBooks Online** ✅
- **Xero Accounting V2** (Beta) ✅

#### 2. Generic Extractor/Writer
Pro systémy s REST API bez dedikovaného komponentu:
- **Pohoda Cloud (mPOHODA)**
- **Sage 50 AT** (přes HyperAccounts)

**Dokumentace:**
- Generic Extractor: https://developers.keboola.com/extend/generic-extractor/

#### 3. MCP Integration
Model Context Protocol integrace:
- **Dokumentace:** https://developers.keboola.com/integrate/mcp/

#### 4. Custom Components
Pro komplexní případy:
- **Money S3/S4/S5** (GraphQL)
- **Helios iNuvio**
- **BMD**
- **Mesonic WinLine**

### Keboola Resources

**Developer Portal:**
- Components list: https://components.keboola.com/components
- API: https://developers.keboola.com/overview/api/
- CLI: https://developers.keboola.com/cli/
- Templates: https://help.keboola.com/templates/

**Integration Tools:**
- CDC (Change Data Capture): https://www.youtube.com/watch?v=zIgsdZtJ-nM
- Data streams: https://developers.keboola.com/integrate/data-streams/overview/

**Use Cases:**
- Financial Intelligence: https://www.keboola.com/solutions/financial-intelligence
- Changelog: https://changelog.keboola.com/

---

## 📊 Summary Tables

### Přehled podle statusu

| ERP Systém | Status v Keboola | Priorita | Časová náročnost | Typ |
|------------|------------------|----------|------------------|-----|
| **PŘIPRAVENO** |
| FlexiBee | ✅ Máme konektor | HIGH | Připraveno | Data source |
| K2 (Karat) | ✅ Máme konektor | HIGH | Připraveno | Data source |
| MS Dynamics 365 BC | ✅ Máme konektor | HIGH | Připraveno | Source + Destination |
| SAP Business One | ✅ Máme konektor | MEDIUM | Připraveno | Custom (vendor) |
| Fakturoid | ✅ Plně podporováno | HIGH | Připraveno | Source + Destination |
| QuickBooks Online | ✅ Připraveno | MEDIUM | Připraveno | Data source |
| Xero | ✅ Beta | MEDIUM | Připraveno | Data source |
| **RYCHLÁ IMPLEMENTACE** |
| Pohoda Cloud | 💡 Generic možné | HIGH | 1-2 týdny | Generic Extractor+Writer |
| **STŘEDNÍ NÁROČNOST** |
| Pohoda on-prem | 💡 Generic možné | MEDIUM | 2-4 týdny | Generic Extractor+Writer |
| **CUSTOM DEVELOPMENT** |
| Money S3/S4/S5 | ❌ Nemáme | MEDIUM | 1-2 týdny | Custom Extractor+Writer |
| Helios iNuvio | ❌ Nemáme | LOW | 3-4 týdny | Custom (vendor) |
| BMD (AT) | ❌ Nepřipraveno | LOW | 4-6 týdnů | Custom connector |
| RZL (AT) | ❌ Nepřipraveno | LOW | ? | Manual file exchange |
| Mesonic WinLine (AT) | ❌ Nepřipraveno | LOW | 4-6 týdnů | Custom connector |
| Sage 50 AT | ❌ Nepřipraveno | LOW | Neurčeno | Generic (3rd party) |

### Přehled podle země

#### 🇨🇿 Česká republika

| Systém | Status | API | Demo/Sandbox |
|--------|--------|-----|--------------|
| FlexiBee | ✅ Ready | REST | ✅ Veřejný demo server |
| K2 (Karat) | ✅ Ready | REST | ❌ Vlastní instalace |
| Fakturoid | ✅ Ready | REST | ⚠️ Vlastní účet (2 integrace) |
| Pohoda Cloud | 💡 Generic | REST | ❌ Vyžaduje Pro tarif |
| Pohoda on-prem | 💡 Generic | XML | ❌ Vlastní instalace |
| Money S3/S4/S5 | ❌ Custom | GraphQL | ❌ Vyžaduje modul API |
| Helios iNuvio | ❌ Custom | REST | ❌ Vendor spolupráce |

#### 🇦🇹 Rakousko

| Systém | Status | API | Demo/Sandbox |
|--------|--------|-----|--------------|
| BMD | ❌ Custom | SOAP/XML | ❌ Partner only |
| RZL | ❌ Manual | None | ❌ File export only |
| Mesonic WinLine | ❌ Custom | EXIM modules | ❌ License required |
| Sage 50 AT | ❌ Generic | REST (3rd) | ❌ HyperAccounts |

#### 🌍 International

| Systém | Status | API | Demo/Sandbox |
|--------|--------|-----|--------------|
| MS Dynamics 365 BC | ✅ Ready | REST/OData | ✅ CRONUS sandbox |
| SAP Business One | ✅ Ready | REST/OData | ❌ License required |
| QuickBooks Online | ✅ Ready | REST | ✅ Auto sandbox |
| Xero | ✅ Beta | REST | ✅ Demo Company (28d) |

---

## 💡 Implementation Recommendations

### Prioritizace podle business value

**Tier 1 - Immediate (týdny 1-3):**
1. FlexiBee - nejpoužívanější v ČR
2. MS Dynamics 365 BC - enterprise + právě launchli
3. K2 (Karat) - velký podíl malých/středních firem
4. Fakturoid - freemium, široká adopce

**Tier 2 - Quick wins (týdny 4-6):**
5. Pohoda Cloud - cloudová verze je populární
6. QuickBooks Online - mezinárodní standard
7. Xero - UK/AU trh

**Tier 3 - Custom (týdny 7-12):**
8. Money S3/S4/S5 - velký podíl v ČR
9. SAP Business One - enterprise (už je ready)
10. Pohoda on-prem - legacy instalace

**Tier 4 - Long-term (3+ měsíce):**
11. Helios iNuvio - vyžaduje vendor
12. Rakouské systémy - niche market

### Technická doporučení

**OAuth 2.0 implementace:**
- Fakturoid (Authorization Code + Client Credentials)
- MS Dynamics 365 BC (Azure AD)
- QuickBooks Online
- Xero

**REST API (standardní):**
- FlexiBee
- K2
- mPOHODA
- MS Dynamics BC
- QuickBooks
- Xero

**GraphQL:**
- Money S3 (custom connector needed)

**Legacy/XML:**
- Pohoda on-prem (mServer XML)

**SOAP/File-based:**
- Rakouské systémy (BMD, Mesonic)

---

## 📖 Complete Documentation Links

### Keboola Platform
- Components: https://components.keboola.com/components
- Generic Extractor: https://developers.keboola.com/extend/generic-extractor/
- MCP Integration: https://developers.keboola.com/integrate/mcp/
- API: https://developers.keboola.com/overview/api/
- CLI: https://developers.keboola.com/cli/
- Templates: https://help.keboola.com/templates/
- Data Streams: https://developers.keboola.com/integrate/data-streams/overview/
- CDC: https://www.youtube.com/watch?v=zIgsdZtJ-nM
- Changelog: https://changelog.keboola.com/
- Financial Intelligence: https://www.keboola.com/solutions/financial-intelligence

### ERP Systems Documentation
*(Organized by system, see individual sections above)*

---

**Document Version:** 2.0
**Last Updated:** 2025-11-11
**Maintained by:** Development Team
**Next Review:** On-demand based on vendor updates

## Changelog

### Version 2.0 (2025-11-11)
- ✅ Fixed UTF-8 encoding throughout document
- ✅ Added Python SDK information for QuickBooks (`python-quickbooks`) and Xero (`xero-python`)
- ✅ Enhanced sandbox/demo access details for all systems
- ✅ Added specific API endpoint URLs (e.g., mPOHODA: `https://api.mpohoda.cz/v1`)
- ✅ Clarified FlexiBee developer license (3 months free)
- ✅ Added Fakturoid User-Agent header requirement
- ✅ Documented Money S3 GraphQL synchronous/asynchronous behavior
- ✅ Updated Sage 50 AT with HyperAccounts third-party API details
- ✅ Clarified SAP Business One Service Layer SAP HANA requirement
- ✅ Improved Quick Wins section with priority recommendations for Neobank

### Version 1.0 (2025-11-11)
- Initial version based on research documents
