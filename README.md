# Exchange platform
Piattaforma che permette di scambiare bitcoins con gli altri utenti autenticati pubblicando delle offerte di acquisto e vendita.

## Caratteristiche
Questa piattaforma permette agli utenti autenticati di scambiare bitcoins come se fossere degli oggetti, senza alcun costo di commissine.
Le offerte vengono salvate nel database Mongo, e si connette attraverso il modulo pymongo. Non è stato utilizzato interamente il database
Mongo in quanto le ultime versioni di Django non supportano l'utilizzo dei database non relazionali. Per tanto come database di default
viene utilizzato SQL Lite mentre per memorizzare la maggioranza delle informazioni: offerte, account degli utenti viene utilizzato Mongo.
Offre vari endpoint per le funzionalità che offre:
- permette nel momento della registrazione di ottenere una quantità variabile tra gli 1 e i 10 bitcoins e tra i 40 e 60 moneta fiat.
- gestisce l'autenticazione e l'uscita degli utenti dalla piattaforma
- permette di caricare il proprio account in modo da poter avere abbastanza moneta fiat per scambiare bitcoin
- permette di convertire la propria moneta fiat con nuovi bitcoin con un costo di commissione di 2 fiat; questo per incentivare lo scambio di
bit con gli altri utenti. Lo scambio ha un rapporto di 1:1
- permette di pubblicare delle offerte di vendita e di acquisto per permettere lo scambio di bitcoins, esclusivamente se l'utente ha la quantità
necessaria di bitcoin o fiat in base se l'offerta è di vendita o acquisto
- permette di ottenere un oggetto JSON con tutte le offerte pubblicate
- permette di ottenere un oggetto JSON con la quantità di bitcoins e fiat persa o guadagnata da ogni utente
- permette di ottenere un oggetto JSON con tutti gli utenti autenticati
- permette di ottenere un oggetto JSON con la quantità di bitcoins e fiat attuale dell'utente autenticato

## Funzionalità
Ogni utente ha una quantità di bitcoins e di moneta fiat casuali date nel momento della creazine dell'account che possono utilizzarle per poter
pubblicare delle offerte di vendita o acquisto di bitcoins.
Ogni offerta viene memorizzata nel database MongoDB sotto-forma di oggetto JSON.
Nel momento della memorizzazione dell'offerta vengono svolti tutti i controlli necessari nel caso l'utente abbia abbastanza bitcoins o
moneta fiat. Appenda viene pubblicata un offerta, essa assume uno stato di posizione aperta e nel momento che viene pubblicata una nuova offerta
che rispetta i requisiti della precedente chiude le due posizioni in modo che non possano essere più utilizzate, aggiornando gli account
dei due utenti e concludendo lo scambio dei bitcoins.
Come scritto precedentemente ogni utente ha una propria quantità di bitcoins e moneta fiat al momento della creazione dell'account ma questo
non significa che non possa ottenerne di nuove, infatti ogni utente ha la possibilità di caricare il proprio account con nuova moneta fiat
e di ottenere nuovi bitcoins attraverso lo scambio con gli altri utenti oppure convertendo la moneta fiat con nuovi bitcoins con un tasso di
conversione di 2 monete fiat.
Inoltre ogni utente è a conoscenza dello stato del proprio account, di tutte le offerte memorizzate di tutti gli utenti e di tutti gli utenti
registrati.