# Ventic Provider Template — Contoso Ltd

Repository: [nettersrl/ventic-provider-template](https://github.com/nettersrl/ventic-provider-template).

```sh
git clone git@github.com:nettersrl/ventic-provider-template.git
cd ventic-provider-template
```

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

Per una nuova installazione creare un fork GitHub o usare questo template in un repository distinto,
scegliere nome/namespace univoci e sostituire Contoso in `config/` e `artwork/`.
Non copiare mai un provider reale, `.git`, `.build/`, `private/`, credenziali,
snapshot o backup. Impostare `VERSION` tramite
`make version-set VERSION=0.1.0`; per gli aggiornamenti incrementare SemVer.
I backend/frontend possono avere versioni diverse: il lock descrive la combinazione.

Lo stack fissa backend `0.1.0`, frontend `1.1.2` e common `1.0.0`.
I commit completi, i checksum del bundle frontend e il suo URL immutabile sono
in `stack.lock.json`. I consumer puntano al common pubblicato; il bundle identifica
il commit frontend pulito. La CI frontend pubblica il pacchetto dipendenza dopo
le verifiche: un pacchetto ancora in attesa non viene considerato disponibile.

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

GitHub Actions esegue i test offline del template e verifica i piani incompleti
senza credenziali, accesso al cluster o checkout dei sorgenti privati della
piattaforma. Il deploy rimane esplicito tramite i comandi Makefile, dopo aver
fornito gli input dell'ambiente. Il workflow non carica `private/`, log o cache
come artefatti e non esegue deploy da pull request.

Per sviluppo da sorgente, backend/frontend e il pacchetto dipendenza restano nei
repository GitLab fissati in `stack.lock.json`: l'accesso a quei repository è
separato dal fork GitHub. La `.gitlab-ci.yml` e gli helper GitLab sono conservati
come compatibilità opzionale per mirror GitLab; non sono il workflow GitHub e
richiedono runner, variabili File e tag protetti configurati dal proprietario.

La sandbox `ventic-contoso-local` usa il solo profilo locale, porta 9443,
`https://portal.contoso.ventic.localhost:9443` e credenziali generate; non usa i
file privati di produzione. Eseguire i target `sandbox-*` solo dopo aver importato
il bundle frontend fissato e installato i prerequisiti locali della piattaforma.

## English

This is a fictional **Contoso Ltd** installation template, with original generic
artwork and no Microsoft branding, credentials or legal terms. Fork or use the GitHub template in a new repository, keeping only public template files, then choose unique installation,
namespace, domains, artwork and environment settings. Never copy a live provider's
private inputs, Git history, build state or backups.

The provider's SemVer `VERSION` identifies its installation release. Exact backend,
frontend, common and frontend artifact pins live in `stack.lock.json`.
`make sources-fetch` uses only those commits; `make stack-check` rejects mismatches
and dirty upstream sources. Update pins from clean, published checkouts using
`scripts/sources.py pin --backend-dir ... --frontend-dir ...`.
The current lock selects backend 0.1.0, frontend 1.1.2 and common 1.0.0, with
full published source commits and the clean frontend bundle checksum/immutable URL.
Frontend CI publishes that dependency package after verification; a pending package
is not treated as available. The AGENTS.md push procedure updates this full chain.

`make deploy-plan ENVIRONMENT=staging` is offline and lists missing owner inputs.
Supply real public configuration, approved legal documents, licensing, operators,
DNS/TLS, OpenBao, a signed backend release and environment-specific private files.
Configure separate values/installations for staging and production. Targets use
the Kubernetes API and credentials directly, optionally through a verified SSH
tunnel; they never execute host deployment scripts. Helm retains both platform
leases, operator schedules and journals.

GitHub Actions runs the template unit tests and offline deployment plans without
cluster credentials or private platform checkouts. Deployment remains an explicit
Makefile operation with owner-supplied inputs; pull requests cannot deploy.
The workflow uploads no private inputs, logs or caches. Pinned backend/frontend
sources still live on GitLab and require separate access for source development.
The retained GitLab pipeline/helpers are optional mirror compatibility only and
need separately configured protected runners/tags and File variables. No cloud
access or live deployment is provisioned by the GitHub workflow. Local sandbox
state and generated credentials remain isolated from production.


Backup e recupero / Backup and recovery: `make backup-init`, `backup-full`,
`backup-incremental`, `backup-list`, `backup-verify`, `restore-plan`.
Copy `config/backup.example.json` to ignored `private/backup.json` and complete
its explicit cluster identity, off-host HTTPS repository and private references.
OpenBao recovery material and backup keys remain in `private/` (0700/0600), never
in Git or published artifacts. S3 contents are optional with `ARGS=--include-s3`.
The workflow pauses installation writers for a consistent checkpoint; it never
backs up another installation implicitly. Incrementals deduplicate complete source
snapshots; physical database/WAL backups remain complementary.
See the Ventic frontend guide `docs/provider-settings-and-recovery.md` for custody,
configuration migration, exact backup coverage and verification limitations.


## Installazione binaria / Binary installation

Per i clienti usare la [guida completa IT/EN](https://gitlab.com/nettersrl/ventic/ventic-frontend/-/blob/main/apps/docs/content/provider/redistribuzione.md).
Impostare `config/distribution.yaml`, ottenere la chiave pubblica release da un
canale fidato e salvarla in `private/release.pub`. Eseguire `python3 -m pip install
-r requirements-installer.txt`, `make release-fetch`, `make release-check`, quindi
completare il piano/deploy dell'ambiente con `distribution: true`.
Questo percorso verifica e usa immagini/installer compilati; non clona o compila
backend/frontend. `stack.lock.json` e `sources-fetch` restano per sviluppo.

English: configure the signed release version/origin, independently pin the release
public key, install the Python installer dependencies, and run `release-fetch` /
`release-check` before environment deployment. Binary installations do not require
platform sources or compilers. A template version is not evidence of publication.
