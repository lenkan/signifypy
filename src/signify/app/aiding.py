from math import ceil

from keri import kering
from keri.app.keeping import Algos
from keri.core import eventing
from keri.core.coring import Tiers, MtrDex, Tholder
from keri.kering import Roles
from requests import exceptions

from signify.app.clienting import SignifyClient


class Identifiers:
    """ Domain class for accessing, creating and rotating KERI Autonomic IDentifiers (AIDs) """

    stem = "signify:aid"

    def __init__(self, client: SignifyClient):
        self.client = client

    def list(self):
        res = self.client.get("/identifiers")
        return res.json()

    def get(self, name):
        res = self.client.get(f"/identifiers/{name}")
        return res.json()

    def create(self, name, transferable=True, isith="1", nsith="1", wits=None, toad="0", proxy=None, delpre=None,
               dcode=MtrDex.Blake3_256, data=None, algo=Algos.salty, **kwargs):

        aid = dict(
            transferable=transferable,
            state=dict(
                k=[""],
                ee=dict(
                    s="0"
                )
            ),
        )

        # Get the algo specific key params
        aid[algo] = self._keys(algo, **kwargs)

        keys = self.client.manager.keys(0, aid)
        ndigs = self.client.manager.ndigs(aid)

        wits = wits if wits is not None else []
        data = [data] if data is not None else []
        if delpre is not None:
            serder = eventing.delcept(delpre=delpre,
                                      keys=keys,
                                      isith=isith,
                                      nsith=nsith,
                                      ndigs=ndigs,
                                      code=dcode,
                                      wits=wits,
                                      toad=toad,
                                      data=data)
        else:
            serder = eventing.incept(keys=keys,
                                     isith=isith,
                                     nsith=nsith,
                                     ndigs=ndigs,
                                     code=dcode,
                                     wits=wits,
                                     toad=toad,
                                     data=data)

        sigs = self.client.manager.sign(serder.raw, aid)

        json = dict(
            name=name,
            icp=serder.ked,
            sigs=sigs,
            proxy=proxy)
        json[algo] = aid[algo]

        self.client.pidx = self.client.pidx + 1

        res = self.client.post("/identifiers", json=json)
        return res.json()

    def _keys(self, algo, **kwargs):
        match algo:
            case Algos.salty:
                return self._saltyKeys(**kwargs)
            case Algos.randy:
                return self._randyKeys(**kwargs)
            case Algos.group:
                return self._groupKeys(**kwargs)

    def _saltyKeys(self, tier=Tiers.low, icodes=None, ncodes=None, dcode=MtrDex.Blake3_256,
                   count=1, code=MtrDex.Ed25519_Seed,
                   ncount=1, ncode=MtrDex.Ed25519_Seed):
        if not icodes:  # if not codes make list len count of same code
            icodes = [code] * count
        if not ncodes:
            ncodes = [ncode] * ncount

        salt = dict(
            stem=self.stem,
            tier=tier,
            pidx=self.client.pidx,
            icodes=icodes,
            ncodes=ncodes,
            dcode=dcode,
        )

        return salt

    @staticmethod
    def _randyKeys(states, rstates):
        pass

    @staticmethod
    def _groupKeys(mhab, states, rstates):

        keys = [state['k'][0] for state in states]
        smids = [state['i'] for state in states]

        ndigs = [state['n'][0] for state in rstates]
        rmids = [state['i'] for state in rstates]

        return dict(
            mhab=mhab,
            keys=keys,
            ndigs=ndigs,
            smids=smids,
            rmids=rmids
        )

    def update(self, name, typ, **kwas):
        if typ == "interact":
            self.interact(name, **kwas)
        elif typ == "rotate":
            self.rotate(name, **kwas)
        else:
            raise kering.KeriError(f"{typ} invalid identifier update type, only 'rotate' or 'interact' allowed")

        pass

    def delete(self, name):
        pass

    def interact(self, name, data=None):
        hab = self.get(name)
        pre = hab["prefix"]

        state = hab["state"]
        sn = int(state["s"], 16)
        dig = state["d"]

        data = data if isinstance(data, list) else [data]

        serder = eventing.interact(pre, sn=sn + 1, data=data, dig=dig)
        sigs = self.client.manager.sign(ser=serder.raw, aid=hab)

        json = dict(
            ixn=serder.ked,
            sigs=sigs)

        res = self.client.put(f"/identifiers/{name}?type=ixn", json=json)
        return res.json()

    def rotate(self, name, *, isith=None, nsith=None, ncount=1, toad=None, cuts=None, adds=None,
               data=None):
        hab = self.get(name)
        pre = hab["prefix"]

        state = hab["state"]
        count = len(state['k'])
        dig = state["d"]
        ridx = int(state["ee"]["s"], 16) + 1
        wits = state['b']
        sith = state["kt"]

        if isith is None:
            isith = sith  # use prior next sith as default
        if nsith is None:
            nsith = isith  # use new current as default

        if isith is None:  # compute default from newly rotated verfers above
            isith = f"{max(1, ceil(count / 2)):x}"
        if nsith is None:  # compute default from newly rotated digers above
            nsith = f"{max(0, ceil(ncount / 2)):x}"

        cst = Tholder(sith=isith).sith  # current signing threshold
        nst = Tholder(sith=nsith).sith  # next signing threshold

        # Regenerate next keys to sign rotation event
        keys = self.client.manager.keys(count, count, hab)
        # Create new keys for next digests
        ndigs = self.client.manager.ndigs(ncount, ncount, hab)

        cuts = cuts if cuts is not None else []
        adds = adds if adds is not None else []
        data = [data] if data is not None else []
        serder = eventing.rotate(pre=pre,
                                 keys=keys,
                                 dig=dig,
                                 sn=ridx,
                                 isith=cst,
                                 nsith=nst,
                                 ndigs=ndigs,
                                 toad=toad,
                                 wits=wits,
                                 cuts=cuts,
                                 adds=adds,
                                 data=data)
        sigs = self.client.manager.sign(ser=serder.raw, aid=hab)

        json = dict(
            rot=serder.ked,
            sigs=sigs)

        res = self.client.put(f"/identifiers/{name}", json=json)
        return res.json()

    def addEndRole(self, name, *, role=Roles.agent, eid=None):
        hab = self.get(name)
        pre = hab["prefix"]

        rpy = self.makeEndRole(pre, role, eid)
        sigs = self.client.manager.sign(ser=rpy.raw, aid=hab)
        json = dict(
            rpy=rpy.ked,
            sigs=sigs
        )

        try:
            res = self.client.post(f"/identifiers/{name}/endroles", json=json)
            return res.json()
        except exceptions.HTTPError as e:
            print(e.response.json())

    @staticmethod
    def makeEndRole(pre, role=Roles.agent, eid=None):
        data = dict(cid=pre, role=role)
        if eid is not None:
            data['eid'] = eid

        route = "/end/role/add"
        return eventing.reply(route=route, data=data)
