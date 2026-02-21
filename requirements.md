Milestone #2 (January-March 01)

Generally, the system should operate as a service through API calls. Aside from that, the focus of this milestone is to create functionality that supports a human-in-the-loop process. Since we cannot expect any system to perfectly extract the desired information that different people might want, the system should be designed in a way that faciliates user selection, customization, and corrections. The additional requirements are below.

The system must be able to ... :

    Allow incremental information by adding another zipped folder of files for the same portfolio or résumé that incorporates additional information at a later point in time
    Recognize duplicate files and maintains only one in the system
    Allow users to choose which information is represented (e.g., re-ranking of projects, corrections to chronology, attributes for project comparison, skills to highlight, projects selected for showcase)
    Incorporate a key role of the user in a given project
    Incorporate evidence of success (e.g., metrics, feedback, evaluation) for a given project
    Allow user to associate a portfolio image for a given project to use as the thumbnail
    Customize and save information about a portfolio showcase project
    Customize and save the wording of a project used for a résumé item
    Display textual information about a project as a portfolio showcase
    Display textual information about a project as a résumé item
    Use a FastAPI to faciliate the communication between the backend and the frontend
    Support API endpoints for:
        POST /projects/upload
        POST /privacy-consent
        GET /projects
        GET /projects/{id}
        GET /skills
        GET /resume/{id}
        POST /resume/generate
        POST /resume/{id}/edit
        GET /portfolio/{id}
        POST /portfolio/generate
        POST /portfolio/{id}/edit 
    Exact wording and use of {id} can vary. You may also decide to have more endpoints. 

## Milestone 2 Coverage Assessment (API vs Frontend)

| Requirement | API | Frontend |
|---|---|---|
| Incremental upload for same project/portfolio | Implemented | Partial (can re-upload with same project name, but no explicit incremental snapshot UX) |
| Duplicate file recognition / single stored copy | Implemented | N/A (backend behavior) |
| User choice of represented info (ranking/chronology/compare attrs/highlights/showcase selection) | Implemented | Missing UI/config controls |
| Key user role per project | Implemented | Missing editor UI |
| Evidence of success (metrics/feedback/evaluation) | Implemented | Missing editor UI |
| Portfolio thumbnail image association | Implemented | Missing upload/delete UI |
| Customize/save portfolio showcase wording | Implemented | Missing UI |
| Customize/save resume wording | Implemented | Missing UI |
| Display textual portfolio showcase | Implemented | Partial (top view does not use generated showcase edit/display flow) |
| Display textual resume item | Implemented | Partial (PDF generation flow exists, but no in-app text view/edit flow) |
| FastAPI service for backend/frontend communication | Implemented | Consumed |

### Required Endpoint Checklist

All required endpoints are present in API:
- `POST /projects/upload`
- `POST /privacy-consent`
- `GET /projects`
- `GET /projects/{id}`
- `GET /skills`
- `GET /resume/{id}`
- `POST /resume/generate`
- `POST /resume/{id}/edit`
- `GET /portfolio/{id}`
- `POST /portfolio/generate`
- `POST /portfolio/{id}/edit`

### Bottom Line

1. Missing in API: no major requirement gaps found.
2. Missing in frontend: several human-in-the-loop workflows are still absent (config/ranking/chronology/compare controls, role/evidence editing, thumbnail management, resume/portfolio edit flows, generated artifact text views).
