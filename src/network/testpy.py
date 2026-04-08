import posix_ipc, mmap, struct, time

# --- MODIFICATION DU FMT ---
# generals(3i) + map_w(i) + map_h(i) + scenario(100s) + 10*units(iiffi) + nb_u(i) + ready(i) + updated(i)
FMT = "3i" + "ii" + "100s" + ("iiffi" * 10) + "iii"
SIZE = struct.calcsize(FMT)

def run_ia():
    # Note: Assure-toi que le programme C a bien créé le SHM avant
    shm = posix_ipc.SharedMemory("/medieval_shm")
    sem = posix_ipc.Semaphore("/medieval_sem")
    memory = mmap.mmap(shm.fd, SIZE)

    print("[Python] IA connectée.")

    try:
        while True:
            sem.acquire() # [cite: 45]
            
            raw_data = memory[:SIZE]
            unpacked = struct.unpack(FMT, raw_data)
            
            # --- MODIFICATION DE L'INDEXATION ---
            # Dans le nouveau FMT, world_updated est le tout dernier élément (-1)
            world_updated = unpacked[-1] 
            
            if world_updated:
                # nb_units est l'avant-avant-dernier élément (-3)
                nb_units = unpacked[-3] 
                scenario = unpacked[5].decode('utf-8').strip('\x00')
                print(f"[Python] Vision du monde ({scenario}): {nb_units} unités.")

            # --- MODIFICATION DE L'ENVOI ---
            generals = [0, 1, 2]
            # On prépare 10 unités (ici vides pour l'exemple)
            unit_values = [0, 0, 0.0, 0.0, 0] * 10 
            
            # Construction de la ligne action_data
            # On utilise .encode() pour le char[100] du C
            action_data = struct.pack(FMT, *generals, 120, 120, b"far_armies", *unit_values, 5, 1, 0)
            
            memory.seek(0)
            memory.write(action_data)

            sem.release() # [cite: 43]
            time.sleep(1)

    except KeyboardInterrupt:
        print("Arrêt.")

if __name__ == "__main__":
    run_ia()