"""Local moderation using server database credentials, never browser credentials."""
import argparse
import json
from pathlib import Path
from uuid import UUID
import sqlalchemy as sa
import database
from feedback_export import export_feedback


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('pending')
    for action in ('approve', 'reject', 'remove', 'status', 'link'):
        command = commands.add_parser(action)
        command.add_argument('id', type=UUID)
        if action == 'approve':
            command.add_argument('--origin', required=True, choices=['community', 'developer', 'test'])
            command.add_argument('--note', required=True)
        elif action == 'status':
            command.add_argument('status', choices=['suggested', 'planned', 'in_progress', 'released'])
            command.add_argument('--note', required=True)
        elif action == 'link':
            command.add_argument('roadmap_key', choices=sorted(database.ROADMAP_KEYS))
    commands.add_parser('export').add_argument('output', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == 'pending':
            with database.get_connection() as conn:
                rows = conn.execute(sa.select(database.feedback).where(database.feedback.c.moderation_status == 'pending')
                    .order_by(database.feedback.c.created_at).limit(100)).mappings().all()
            # JSON escaping prevents user-submitted terminal control characters from executing.
            print(json.dumps([dict(row) for row in rows], default=str, ensure_ascii=True))
        elif args.command == 'export':
            export_feedback(args.output)
            print('Private export created.')
        else:
            database.moderate_feedback(str(args.id), args.command, origin=getattr(args, 'origin', None),
                status=getattr(args, 'status', None), roadmap_key=getattr(args, 'roadmap_key', None), note=getattr(args, 'note', ''))
            print('Moderation updated. Only consented, approved reviews/features with verified origin can appear publicly.')
    except ValueError as error:
        parser.exit(1, str(error) + '\n')
    except Exception:
        parser.exit(1, 'Moderation failed. Check database access; no credentials are printed.\n')


if __name__ == '__main__':
    main()
