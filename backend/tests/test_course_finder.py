from services import course_finder as course_finder_module
from services.course_finder import CourseFinderService


def make_course_finder(monkeypatch):
    def fake_generate_roadmap(profession, student_raw_skills, profession_profile):
        return {
            "gap": {
                "libraries": ["pytorch"],
            },
            "full": {
                "libraries": ["pytorch"],
            },
        }

    service = CourseFinderService.__new__(CourseFinderService)
    service.profession_profiles = {
        "Machine Learning Engineer": {
            "libraries": ["pytorch"],
        }
    }
    service._find_courses_en = lambda skill, *args, **kwargs: [{"title": f"{skill} English course"}]
    service._find_courses_ru = lambda skill, *args, **kwargs: [{"title": f"{skill} Russian course"}]

    monkeypatch.setattr(course_finder_module, "generate_roadmap", fake_generate_roadmap)
    return service


def test_english_interface_uses_english_courses(monkeypatch):
    service = make_course_finder(monkeypatch)

    roadmap, full_roadmap = service.get_roadmap_with_courses(
        profession="Machine Learning Engineer",
        student_skills=["python"],
        lang="en",
    )

    assert full_roadmap == {"libraries": ["pytorch"]}
    assert roadmap["libraries"]["pytorch"]["courses"][0]["title"] == "pytorch English course"


def test_russian_interface_uses_russian_courses(monkeypatch):
    service = make_course_finder(monkeypatch)

    roadmap, _ = service.get_roadmap_with_courses(
        profession="Machine Learning Engineer",
        student_skills=["python"],
        lang="ru",
    )

    assert roadmap["libraries"]["pytorch"]["courses"][0]["title"] == "pytorch Russian course"


def test_kazakh_interface_reuses_russian_courses(monkeypatch):
    service = make_course_finder(monkeypatch)

    roadmap, _ = service.get_roadmap_with_courses(
        profession="Machine Learning Engineer",
        student_skills=["python"],
        lang="kk",
    )

    assert roadmap["libraries"]["pytorch"]["courses"][0]["title"] == "pytorch Russian course"
