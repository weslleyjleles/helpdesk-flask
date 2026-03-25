import unicodedata

def normalizar_setor(setor):
    if not setor:
        return None
    setor = setor.strip().lower()
    setor = unicodedata.normalize('NFKD', setor).encode('ASCII', 'ignore').decode('utf-8')
    correspondencias = {
        'rh': 'RH',
        'dp': 'DP',
        'financeiro': 'Financeiro',
        'expedicao': 'Expedição',
        'logistica': 'Logística',
        'contabilidade': 'Contabilidade',
        'beneficio': 'Benefício',
    }
    return correspondencias.get(setor, setor.capitalize())
