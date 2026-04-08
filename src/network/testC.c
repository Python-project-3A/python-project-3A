#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <fcntl.h>
#include <semaphore.h>
#include <unistd.h>
#include <string.h>

// {
// 	"generals": [0, 1, 2],
// 	"map_width": 120,
// 	"map_height": 120,
// 	"scenario_name": "far_armies"
// 	"units": [
// 		{
// 			"id": 1,
// 			"hp": 20,
// 			"position": (1, 1),
// 			"owner": 0
// 		}, 
// 		{
// 			"id": 4,
// 			"hp": 40,
// 			"position": (12, 10),
// 			"owner": 1
// 		}
// 	]
// }

struct unit {
    int id;
    int hp;
    float x,y;
    int owner;
    
};

struct Dshare {
    int generals[3];
    int map_width;
    int map_height;
    char scenario[100];
    struct unit units[10];
    int nb_units;
    int world_ready;
    int world_updated;
};

// struct SharedData {
//     // --- Flux : Python -> C (Commandes de l'IA) ---
//     int action_type;  // 1=Move, 2=Attack
//     float target_x, target_y;
//     int action_ready; // Flag pour C : "Il y a un nouvel ordre"

//     // --- Flux : C -> Python (Vision du monde) ---
//     struct Entity entities[10];
//     int nb_entities;
//     int world_updated; // Flag pour Python : "Le monde a changé"
// };

#define SHM_NAME "/medieval_shm"
#define SEM_NAME "/medieval_sem"

int main() {
    int fd = shm_open(SHM_NAME, O_CREAT | O_RDWR, 0666);
    ftruncate(fd, sizeof(struct Dshare));
    struct Dshare *data = mmap(NULL, sizeof(struct Dshare), PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    sem_t *sem = sem_open(SEM_NAME, O_CREAT, 0666, 1);

    printf("[C] Module Réseau actif.\n");

    while(1) {
        sem_wait(sem); // Début section critique (Cohérence)

        // 1. RÉCEPTION depuis Python (Lecture de l'action)
        if (data->world_ready) {
            printf("[C] Action IA reçue : Type %i vers (%f, %f)\n", data->nb_units, data->units[0].x, data->units[0].y);
            data->world_ready = 0; // Accusé de réception
        }

        // 2. ENVOI vers Python (Mise à jour du monde simulée)
        data->generals[0]=0;
        data->generals[1]=1;
        data->generals[2]=2;
        data->map_height=120;
        data->map_width=120;
        strcpy(data->scenario, "far_armies");
        // data->scenario="far_armies";
        data->nb_units=10;
        // data->units=malloc(data->nb_units*(sizeof(struct unit)));
        for(int i=0;i<data->nb_units;i++)
        {
            data->units[i].id=i;
            data->units[i].hp=20;
            data->units[i].x=i+20;
            data->units[i].y=i+20;
            data->units[i].owner=0;
        }
        data->world_updated = 1; // Signal à Python


        sem_post(sem); // Fin section critique [cite: 10, 41]
        usleep(100000); // 100ms
    }
    return 0;
}