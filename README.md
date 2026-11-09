# Ventic — Contoso Ltd

## Italiano

Template di installazione per la società fittizia **Contoso Ltd**, usata come
esempio; non è un'installazione Microsoft e non contiene i suoi marchi o termini.
Identità, artwork originale, domini, sandbox e destinazioni CI sono di proprietà
di questo repository. Servizi e frontend arrivano solo dai pin di `stack.lock.json`.

```sh
make help
make version                      # release del provider: 0.1.0
make deploy-plan ENVIRONMENT=staging  # offline: elenca i prerequisiti mancanti
make sources-fetch                # clona esclusivamente i commit fissati
make stack-check
make test PYTHON=python3          # offline; Python 3.12+ e PyYAML
```

Per una nuova installazione copiare questo template in un repository distinto,
scegliere nome/namespace univoci e sostituire Contoso in `config/` e `artwork/`.
Non copiare mai un provider reale, `.git`, `.build/`, `private/`, credenziali,
snapshot o backup. Impostare `VERSION` tramite
`make version-set VERSION=0.1.0`; per gli aggiornamenti incrementare SemVer.
I backend/frontend possono avere versioni diverse: il lock descrive la combinazione.

I pin iniziali sono backend `0.1.0` a `baaa37bcb5441c1ea02cacca7a16dfefecee37da`,
frontend `1.0.0` a `c279098894af5f3826f2c33b4df49faa3f607482`, common `1.0.0`
a `1df9dd988229c049aec8302f00a1b92fccb2c215`, e bundle frontend storico
`1.0.10-cli-downloads` con checksum esatto. Le modifiche di questa migrazione
richiedono commit pubblicati e un nuovo bundle coerente prima di aggiornare i pin;
non viene dichiarata una release di modifiche ancora non committate.

Completare `config/production.yaml` con domini reali, identità del provider,
documenti legali approvati, chiave pubblica Licman e CIDR ingress verificati.
Il prodotto di licenza resta `netter-ai-platform`. Provisionare gli operatori,
storage, DNS/TLS e OpenBao indicati dalla distribuzione prima dell'installazione.
Fornire una release backend firmata, le sue immagini accessibili dal cluster e
input privati separati in `private/<ambiente>/` (0700; file 0600).
Non generare termini legali tramite sostituzione del nome Contoso.

Ogni file in `config/environments/` seleziona valori, contesto, UID del namespace
`kube-system` e directory privata. Il default `kubernetes` usa direttamente l'API
HTTPS e kubeconfig, senza host VPS obbligatorio. Per un'API loopback raggiunta via
SSH usare `transport: ssh-tunnel` e aggiungere:

```yaml
sshTunnel:
  host: contoso-kubernetes  # alias SSH verificato; nessun comando remoto
  localPort: 16443
  remotePort: 6443
```

Il server del kubeconfig deve coincidere con il tunnel e avere TLS verificato.
Per ambienti distinti usare cluster/namespace/valori e credenziali distinti.
Dopo la prima configurazione usare un file `values` diverso per staging/produzione,
con installazioni e domini separati: il template iniziale lascia intenzionalmente
entrambi incompleti. `make deploy-release ENVIRONMENT=staging` verifica firma,
pin, TLS e UID, poi usa Helm con i lease della piattaforma; `deploy-verify` verifica
il rollout. Non usa gli script storici Netter, non esegue bootstrap del VPS e non
provisiona credenziali OpenBao o chiavi di firma.

La CI verifica Rust nei due modi, contratti, frontend e test della distribuzione.
I job manuali di deploy sono disponibili solo su tag protetti uguali a `v<VERSION>`;
sono serializzati per ambiente. Configurare runner protetti e variabili File
con scope staging/production secondo la
[guida versioni e CI](../ventic-frontend/docs/versioning.md).
Il GitLab remoto, i runner, le variabili e i permessi cloud non sono creati dal template.
Non esistono job che pubblichino `private/` o log come artefatti.

La sandbox `ventic-contoso-local` usa il solo profilo locale, porta 9443,
`https://portal.contoso.ventic.localhost:9443` e credenziali generate; non usa i
file privati di produzione. Eseguire i target `sandbox-*` solo dopo aver importato
il bundle frontend fissato e installato i prerequisiti locali della piattaforma.

## English

This is a fictional **Contoso Ltd** installation template, with original generic
artwork and no Microsoft branding, credentials or legal terms. Copy only the
public template files into a new repository, then choose unique installation,
namespace, domains, artwork and environment settings. Never copy a live provider's
private inputs, Git history, build state or backups.

The provider's SemVer `VERSION` identifies its installation release. Exact backend,
frontend, common and frontend artifact pins live in `stack.lock.json`.
`make sources-fetch` uses only those commits; `make stack-check` rejects mismatches
and dirty upstream sources. Update pins from clean, published checkouts using
`scripts/sources.py pin --backend-dir ... --frontend-dir ...`.
The initial lock preserves the existing historical bundle; publish the prepared
stack changes and consistent new bundle before adopting them as new release pins.

`make deploy-plan ENVIRONMENT=staging` is offline and lists missing owner inputs.
Supply real public configuration, approved legal documents, licensing, operators,
DNS/TLS, OpenBao, a signed backend release and environment-specific private files.
Configure separate values/installations for staging and production. Targets use
the Kubernetes API and credentials directly, optionally through a verified SSH
tunnel; they never execute host deployment scripts. Helm retains both platform
leases, operator schedules and journals.

Protected GitLab tags `v<VERSION>` expose manual, serialized environment deployment
jobs after verification. Provision protected runners and environment-scoped File
variables as described in the linked versioning guide. No GitLab remote, runner,
cloud access or live deployment has been provisioned by this template. Local
sandbox state and generated credentials remain isolated from production.
