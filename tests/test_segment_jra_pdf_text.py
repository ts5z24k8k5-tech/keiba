import unittest

from scripts.segment_jra_pdf_text import SegmentationError, segment_expected_races


def header(date="11月30日", year="2099", meeting="7", venue="京都",
           meeting_day="1", race_no="1"):
    return (
        f"{date} 晴 稍重 （{year}年{meeting}{venue}） "
        f"第{meeting_day}日 第{race_no}競走 2歳未勝利\n馬行の合成テキスト"
    )


class StrictRaceSegmentationTests(unittest.TestCase):
    def expected(self, race_id="209908070101", date="2099-11-30",
                 venue="kyoto", race_no=1):
        return {"race_id": race_id, "date": date,
                "venue": venue, "race_no": race_no}

    def test_matches_date_venue_and_race_number(self):
        blocks = segment_expected_races(
            [header() + "\n払戻情報\n" + header(race_no="2")],
            [self.expected()],
        )
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].race_id, "209908070101")
        self.assertEqual(blocks[0].venue, "kyoto")
        self.assertEqual(blocks[0].meeting_no, 7)
        self.assertIn("第1競走", blocks[0].page_text)
        self.assertNotIn("第2競走", blocks[0].page_text)

    def test_accepts_full_width_digits(self):
        text = "１１月３０日 晴 （２０２４年７京都） 第１日 第１競走\n本文"
        blocks = segment_expected_races([text], [self.expected()])
        self.assertEqual(blocks[0].race_date, "2099-11-30")

    def test_rejects_wrong_date_even_if_race_number_matches(self):
        with self.assertRaisesRegex(SegmentationError, "identity mismatch"):
            segment_expected_races(
                [header(date="12月01日")], [self.expected()]
            )

    def test_rejects_wrong_venue_even_if_race_number_matches(self):
        with self.assertRaisesRegex(SegmentationError, "identity mismatch"):
            segment_expected_races(
                [header(venue="阪神")], [self.expected()]
            )

    def test_rejects_missing_target_heading(self):
        with self.assertRaisesRegex(SegmentationError, "not found"):
            segment_expected_races(["開催情報のみ"], [self.expected()])

    def test_rejects_duplicate_race_heading(self):
        with self.assertRaisesRegex(SegmentationError, "duplicate race heading"):
            segment_expected_races(
                [header() + "\n" + header()], [self.expected()]
            )

    def test_rejects_duplicate_target_id(self):
        with self.assertRaisesRegex(SegmentationError, "duplicate target race_id"):
            segment_expected_races(
                [header()], [self.expected(), self.expected()]
            )

    def test_rejects_race_number_conflicting_with_race_id(self):
        with self.assertRaisesRegex(SegmentationError, "conflicts with race_id"):
            segment_expected_races(
                [header()], [self.expected(race_no=2)]
            )

    def test_rejects_malformed_race_id(self):
        with self.assertRaisesRegex(SegmentationError, "malformed"):
            segment_expected_races([header()], [{"race_id": "bad"}])


if __name__ == "__main__":
    unittest.main()
