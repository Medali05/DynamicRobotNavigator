"""
File de priorité à seaux (« bucket queue »), faite pour des priorités ENTIÈRES.

Idée : un seau par valeur de priorité. Ajouter = ajouter à la fin du seau (O(1)). Extraire = prendre dans le
premier seau non vide : le curseur ne fait qu'avancer quand les priorités extraites sont croissantes, ce qui est
le cas dans notre recherche (coûts entiers, heuristique cohérente). Résultat : O(1) amorti, là où un tas binaire
coûte O(log n), et on stocke des entiers, pas des tuples (f, h, ordre, case).

Départage : à priorité égale, on sort le dernier arrivé (LIFO) : on préfère les cases découvertes le plus
récemment, donc les plus avancées vers la cible.
"""


class FileASeaux:
    __slots__ = ("seaux", "courant", "taille")

    def __init__(self):
        self.seaux = {}      # priorité -> liste de cases
        self.courant = 0     # plus petite priorité possiblement non vide
        self.taille = 0

    def push(self, priorite: int, case: int):
        seau = self.seaux.get(priorite)
        if seau is None:
            self.seaux[priorite] = [case]
        else:
            seau.append(case)
        self.taille += 1
        if priorite < self.courant:
            self.courant = priorite

    def pop(self) -> int:
        seaux, f = self.seaux, self.courant
        while True:
            seau = seaux.get(f)
            if seau:
                break
            if seau is not None:
                del seaux[f]
            f += 1
        self.courant = f
        self.taille -= 1
        return seau.pop()

    def __bool__(self) -> bool:
        return self.taille > 0
