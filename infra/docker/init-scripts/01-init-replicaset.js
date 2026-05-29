// Inizializza il replica set MongoDB per CCI/AVCS
// Questo script viene eseguito dal container mongodb al primo avvio.

// Attendi che mongod sia pronto
let retries = 30;
while (retries-- > 0) {
  try {
    const status = rs.status();
    if (status.ok) break;
  } catch (e) {
    if (retries === 0) throw e;
    sleep(2000);
  }
}

// Inizializza rs0 se non ancora configurato
try {
  rs.status();
  print("Replica set già inizializzato");
} catch (e) {
  rs.initiate({
    _id: "rs0",
    members: [{ _id: 0, host: "mongodb:27017", priority: 1 }],
  });
  print("Replica set rs0 inizializzato");

  // Attendi PRIMARY
  let maxWait = 30;
  while (maxWait-- > 0) {
    const status = rs.status();
    if (status.myState === 1) {
      print("Nodo PRIMARY pronto");
      break;
    }
    sleep(1000);
  }
}
