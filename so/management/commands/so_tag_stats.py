
import csv
import xml.sax
import sys

from django.core.management.base import BaseCommand, CommandError

from so import models


class Command(BaseCommand):
    help = 'Collect historical data for the specified tag. ' \
           'Prints CSV to stdout.'
    requires_system_checks = True  # change to False for xml processing

    def add_arguments(self, parser):
        parser.add_argument('tag', help='tags to return stats for')
        # not implemented yet
        parser.add_argument('-s', '--smoothing', default=0,
                            help='Moving average smoothing, months ')
        parser.add_argument('-m', '--min-score', type=int, nargs='?',
                            help='Moving average smoothing, months ')
        parser.add_argument('-n', '--norm', nargs='?',
                            help='tag to normalize for. Use "all" for total '
                                 'number of posts, omit option for none')

    def _handle(self, *args, **options):
        # 17m to process Posts.xml vs 5..10m for database
        # 13m is SAX parser, reading is only 5 seconds
        from collections import defaultdict

        tag = options['tag']
        norm = options.get('norm')
        min_score = options.get('min-score', -255)

        # [month] = [questions, users, new_users, answers, users, new_users,
        #           # same 6 for norm // if there is norm
        #           # same 6 normalized // if there is norm]
        # This is rather unreadable but since I'm going to process 50Gb of xml
        # for every tag I'm more concerned about performance
        if norm is None:
            columns = ["Month", "questions", "askers", "new_askers",
                       "answers", "responders", "new_responders"]
            stats = defaultdict(lambda: [0]*6)
        else:
            stats = defaultdict(lambda: [0]*18)
            columns = ["Month", "questions", "askers", "new_askers",
                       "answers", "responders", "new_responders",
                       "norm_questions", "norm_askers", "norm_new_askers",
                       "norm_answers", "norm_responders", "norm_new_responders",
                       "nquesions", "naskers", "nnew_askers",
                       "nanswers", "nresponders", "nnew_responders"]

        writer = csv.writer(sys.stdout)
        writer.writerow(columns)

        # [question][norm] = (ids, users, users_this_month)
        temp_stats = [[[set(), set(), set()] for n in (0, 1)]
                      for q in (0, 1)]

        def writerecord(month, record):
            if norm and any(record):
                for i in range(6):  # in procent
                    record[12+i] = round(100.0 * record[i] / record[6+i], 2)
                writer.writerow([month] + record)
            sys.stdout.flush()

        class SOHandler(xml.sax.ContentHandler):
            month = None

            def startElement(self, name, attrs):
                if name != 'row':
                    return  # ignore all other tags

                month = attrs['CreationDate'][:7]
                if month != self.month:
                    if month < self.month:
                        return  # ~1.5K records out of 33M, safe to ignore
                    if self.month is not None:
                        for q in (0, 1):
                            for n in ((0, 1) if norm else [0]):
                                i = 6*n + 3*(1-q)
                                stats[self.month][1+i] = \
                                    len(temp_stats[q][n][2])
                                stats[self.month][2+i] = \
                                    len(temp_stats[q][n][2].difference(
                                        temp_stats[q][n][1]))
                                temp_stats[q][n][1].update(temp_stats[q][n][2])
                                temp_stats[q][n][2] = set()
                        writerecord(month, stats[self.month])
                    self.month = month

                def magic(post_id, user, q, n):
                    if q:
                        temp_stats[1][n][0].add(post_id)
                    temp_stats[q][n][2].add(user)  # users this month
                    stats[month][3 - q*3 + n*6] += 1

                is_question = int(attrs.get('PostTypeId') == "1")
                post_id = int(attrs['Id'])
                # 88723 records out of 33M records don't have OwnerId
                user = attrs.get('OwnerUserId')

                if is_question:
                    # using set() on a short list is ~10 times slower
                    tags = [t.lstrip("<")
                            for t in attrs.get('Tags', "").split(">") if t]
                    # TODO: filter by score
                    # if min_score > int(attrs.get('score', '0')):
                    #     return
                    if tag in tags:
                        magic(post_id, user, 1, 0)
                    if norm and (norm in tags or norm == 'all'):
                        magic(post_id, user, 1, 1)
                elif attrs.get('PostTypeId') == "2":  # rarely there are others
                    parent = int(attrs['ParentId'])
                    if parent in temp_stats[1][0][0]:
                        magic(post_id, user, 0, 0)
                    if parent in temp_stats[1][1][0]:
                        magic(post_id, user, 0, 1)

        parser = xml.sax.make_parser()
        parser.setContentHandler(SOHandler())

        fh = open('so/Posts.xml', 'r')
        parser.parse(fh)
        # parser.parse(sys.stdin)

        # TODO: smoothing
        # for month in sorted(stats):
        #     writer.writerow([month] + stats[month])

    def handle(self, *args, **options):
        try:
            tag = models.Tag.objects.get(name=options['tag'])
        except models.Tag.DoesNotExist:
            raise CommandError('Tag does not exist')

        # date: (questions, askers, new_askers)

        def stats(qs):
            stats_total = {}
            users_total = set()
            users_this_month = set()
            this_month = None
            stats_this_month = None

            for owner, created_at in qs.values_list('owner', 'created_at'):
                date = created_at.strftime("%Y-%m")
                if date != this_month:
                    if this_month is not None:
                        stats_total[this_month] = stats_this_month
                    this_month = date
                    # questions, #unique users this month, #new users this month
                    stats_this_month = [0, 0, 0]
                    users_this_month = set()

                stats_this_month[0] += 1  # number of questions
                stats_this_month[1] += owner not in users_this_month
                users_this_month.add(owner)
                stats_this_month[2] += owner not in users_total
                users_total.add(owner)

            return stats_total

        questions_qs = tag.posts.order_by('created_at')
        question_stats = stats(questions_qs)
        question_ids = questions_qs.values_list('id', flat=True)
        answer_stats = stats(
            models.Post.objects.filter(parent_id__in=question_ids))

        writer = csv.writer(self.stdout)
        # header
        writer.writerow(["Month", "questions", "askers", "new_askers",
                      "answers", "responders", "new_responders"])

        dates = set(question_stats.keys() + answer_stats.keys())
        for date in sorted(dates):
            writer.writerow(
                [date] +
                question_stats.get(date, [0, 0, 0]) +
                answer_stats.get(date, [0, 0, 0]))


if __name__ == '__main__':
    utility = Command(sys.argv[1:])
    utility.execute()
