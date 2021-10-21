import random
from typing import Dict, List
from .image import image_to_base64
from PIL import ImageFont, ImageDraw, Image
from .maimaidx_music import total_list
import os
import requests

hot_music_ids = ['17', '56', '62', '66', '70', '71', '100', '101', '107', '109', '115', '117', '122', '138', '143', '187', '188', '189', '193', '198', '199', '200', '201', '204', '223', '224', '226', '227', '229', '230', '233', '258', '261', '268', '269', '282', '283', '295', '299', '315', '322', '324', '327', '337', '339', '348', '360', '364', '365', '366', '374', '379', '381', '384', '386', '387', '388', '389', '390', '399', '400', '411', '417', '419', '421', '422', '426', '427', '431', '432', '438', '439', '446', '447', '448', '456', '457', '462', '464', '465', '467', '471', '488', '490', '492', '494', '495', '496', '507', '508', '510', '511', '513', '520', '521', '531', '532', '535', '540', '541', '542', '548', '552', '553', '555', '556', '561', '566', '567', '568', '571', '573', '574', '580', '581', '587', '589', '592', '603', '606', '610', '614', '621', '625', '626', '627', '628', '631', '632', '643', '646', '647', '648', '649', '655', '664', '670', '672', '673', '674', '682', '688', '689', '690', '691', '693', '694', '699', '700', '701', '705', '707', '708', '709', '710', '711', '717', '719', '720', '725', '726', '731', '736', '738', '740', '741', '742', '746', '750', '756', '757', '759', '760', '763', '764', '766', '771', '772', '773', '777', '779', '781', '782', '786', '789', '791', '793', '794', '796', '797', '798', '799', '802', '803', '806', '809', '812', '815', '816', '818', '820', '823', '825', '829', '830', '832', '833', '834', '835', '836', '837', '838', '839', '840', '841', '844', '848', '849', '850', '852', '853', '10363', '11002', '11003', '11004', '11005', '11006', '11007', '11008', '11010', '11014', '11015', '11016', '11017', '11018', '11019', '11020', '11021', '11022', '11023', '11024', '11025', '11026', '11027', '11028', '11029', '11030', '11031', '11032', '11034', '11035', '11036', '11037', '11038', '11043', '11044', '11045', '11046', '11047', '11048', '11049', '11050', '11051', '11052', '11058', '11059', '11060', '11061', '11064', '11065', '11067', '11069', '11070', '11073', '11075', '11078', '11080', '11081', '11083', '11084', '11085', '11086', '11087', '11088', '11089', '11090', '11091', '11092', '11093', '11094', '11095', '11096', '11097', '11098', '11099', '11101', '11102', '11103', '11104', '11105', '11106', '11107', '11109', '11110', '11111', '11113', '11114', '11115', '11116', '11121', '11122', '11123', '11124', '11125', '11126', '11127', '11128', '11129', '11131', '11132', '11133', '11134', '11135', '11136', '11137', '11138', '11139', '11140', '11141', '11142', '11143', '11146', '11147', '11148', '11149', '11150', '11151', '11206']
cover_dir = 'src/static/mai/cover/'
# my_data: List = list(filter(lambda x: x['id'] in hot_music_ids, requests.get('https://www.diving-fish.com/api/maimaidxprober/music_data').json()))
# my_data: List = list(obj)

class GuessObject:
    def __init__(self) -> None:
        self.music: Dict = total_list.random()
        self.guess_options = [
            f"的 Expert 难度是 {self.music['level'][2]}",
            f"的 Master 难度是 {self.music['level'][3]}",
            f"的分类是 {self.music['basic_info']['genre']}",
            f"的版本是 {self.music['basic_info']['from']}",
            f"的艺术家是 {self.music['basic_info']['artist']}",
            f"{'不' if self.music['type'] == 'SD' else ''}是 DX 谱面",
            f"{'没' if len(self.music['ds']) == 4 else ''}有白谱",
            f"的 BPM 是 {self.music['basic_info']['bpm']}"
        ]
        self.guess_options = random.sample(self.guess_options, 6)
        pngPath = cover_dir + f"{int(self.music['id'])}.jpg"
        if not os.path.exists(pngPath):
            pngPath = cover_dir + f"{int(self.music['id'])}.png"
        if not os.path.exists(pngPath):
            pngPath = cover_dir + '1000.png'
        img = Image.open(pngPath)
        w, h = img.size
        w2, h2 = int(w / 3), int(h / 3)
        l, u = random.randrange(0, int(2 * w / 3)), random.randrange(0, int(2 * h / 3))
        img = img.crop((l, u, l+w2, u+h2))
        self.b64image = image_to_base64(img)
        self.is_end = False