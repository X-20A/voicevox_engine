"""話者情報機能を提供する API Router"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic.json_schema import SkipJsonSchema

from voicevox_engine.core.core_initializer import CoreManager
from voicevox_engine.metas.Metas import Speaker, SpeakerInfo
from voicevox_engine.metas.MetasStore import Character, MetasStore, ResourceFormat
from voicevox_engine.resource_manager import ResourceManager, ResourceManagerError

RESOURCE_ENDPOINT = "_resources"


async def _get_resource_baseurl(request: Request) -> str:
    return f"{request.url.scheme}://{request.url.netloc}/{RESOURCE_ENDPOINT}"


def _characters_to_speakers(characters: list[Character]) -> list[Speaker]:
    """キャラクターのリストを `Speaker` のリストへキャストする。"""
    return list(
        map(
            lambda character: Speaker(
                name=character.name,
                speaker_uuid=character.uuid,
                styles=character.talk_styles + character.sing_styles,
                version=character.version,
                supported_features=character.supported_features,
            ),
            characters,
        )
    )


def generate_character_router(
    core_manager: CoreManager,
    resource_manager: ResourceManager,
    metas_store: MetasStore,
) -> APIRouter:
    """話者情報 API Router を生成する"""
    router = APIRouter(tags=["その他"])

    @router.get("/speakers")
    def speakers(core_version: str | SkipJsonSchema[None] = None) -> list[Speaker]:
        """話者情報の一覧を取得します。"""
        version = core_version or core_manager.latest_version()
        core = core_manager.get_core(version)
        characters = metas_store.talk_characters(core.characters)
        return _characters_to_speakers(characters)

    @router.get("/speaker_info")
    def speaker_info(
        resource_baseurl: Annotated[str, Depends(_get_resource_baseurl)],
        speaker_uuid: str,
        resource_format: ResourceFormat = "base64",
        core_version: str | SkipJsonSchema[None] = None,
    ) -> SpeakerInfo:
        """
        指定されたspeaker_uuidの話者に関する情報をjson形式で返します。
        画像や音声はresource_formatで指定した形式で返されます。
        """
        version = core_version or core_manager.latest_version()
        core = core_manager.get_core(version)
        return metas_store.character_info(
            character_uuid=speaker_uuid,
            talk_or_sing="talk",
            core_characters=core.characters,
            resource_baseurl=resource_baseurl,
            resource_format=resource_format,
        )

    @router.get("/singers")
    def singers(core_version: str | SkipJsonSchema[None] = None) -> list[Speaker]:
        """歌手情報の一覧を取得します"""
        version = core_version or core_manager.latest_version()
        core = core_manager.get_core(version)
        characters = metas_store.sing_characters(core.characters)
        return _characters_to_speakers(characters)

    @router.get("/singer_info")
    def singer_info(
        resource_baseurl: Annotated[str, Depends(_get_resource_baseurl)],
        speaker_uuid: str,
        resource_format: ResourceFormat = "base64",
        core_version: str | SkipJsonSchema[None] = None,
    ) -> SpeakerInfo:
        """
        指定されたspeaker_uuidの歌手に関する情報をjson形式で返します。
        画像や音声はresource_formatで指定した形式で返されます。
        """
        version = core_version or core_manager.latest_version()
        core = core_manager.get_core(version)
        return metas_store.character_info(
            character_uuid=speaker_uuid,
            talk_or_sing="sing",
            core_characters=core.characters,
            resource_baseurl=resource_baseurl,
            resource_format=resource_format,
        )

    # リソースはAPIとしてアクセスするものではないことを表明するためOpenAPIスキーマーから除外する
    @router.get(f"/{RESOURCE_ENDPOINT}/{{resource_hash}}", include_in_schema=False)
    async def resources(resource_hash: str) -> FileResponse:
        """
        ResourceManagerから発行されたハッシュ値に対応するリソースファイルを返す
        """
        try:
            resource_path = resource_manager.resource_path(resource_hash)
        except ResourceManagerError:
            raise HTTPException(status_code=404)
        return FileResponse(
            resource_path,
            headers={"Cache-Control": "max-age=2592000"},  # 30日
        )

    return router
